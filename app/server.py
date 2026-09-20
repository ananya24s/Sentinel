"""Sentinel demo server.

    python -m uvicorn app.server:app --port 8000      (or ./run.sh)

A small multi-page site (Home, How it works, Attack lab, Activity, Integrate, Benchmark, About) on top of a JSON
API. Scans are serialised with a lock because the models share one accelerator.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
APP = Path(__file__).resolve().parent
STATIC = APP / "static"
ACTIVITY_PATH = ROOT / "data" / "activity.jsonl"

app = FastAPI(title="Sentinel", description="Tool-output trust-boundary defense for LLM agents.")
_state = {"sentinel": None, "error": None, "dataset": None}
_lock = threading.Lock()
_activity: list[dict] = []


def _load():
    try:
        from sentinel.pipeline import Sentinel

        _state["sentinel"] = Sentinel()
    except Exception as e:  # pragma: no cover
        _state["error"] = repr(e)


def _dataset_stats():
    cached = ROOT / "results" / "dataset.json"
    if cached.exists():  # written by scripts/dataset_stats.py; avoids re-parsing the corpus at startup
        _state["dataset"] = json.load(open(cached))
        return
    stats = {}
    for split in ["train", "val", "cal", "test"]:
        p = ROOT / "data/processed" / f"{split}.jsonl"
        if not p.exists():
            continue
        n = poisoned = 0
        fams = set()
        for line in open(p):
            d = json.loads(line)
            n += 1
            if d["kind"] == "poisoned":
                poisoned += 1
                fams.add(d["family"])
        stats[split] = {"docs": n, "poisoned": poisoned, "families": len(fams)}
    _state["dataset"] = stats


@app.on_event("startup")
def startup():
    if ACTIVITY_PATH.exists():
        for line in open(ACTIVITY_PATH).readlines()[-500:]:
            try:
                _activity.append(json.loads(line))
            except ValueError:
                pass
    threading.Thread(target=_load, daemon=True).start()
    threading.Thread(target=_dataset_stats, daemon=True).start()


class ScanReq(BaseModel):
    task: str = Field(max_length=2_000)
    tool_output: str = Field(max_length=200_000)
    source: str = "webpage"
    mode: str = "sentinel"  # sentinel | baseline | both
    origin: str = "api"


class FetchReq(BaseModel):
    url: str = Field(max_length=2_000)
    task: str = Field("Summarize the page.", max_length=2_000)
    mode: str = "sentinel"
    origin: str = "playground"


DEMO_PAGES = [
    {"file": "city-herald.html", "label": "News article", "task": "Summarize the article.",
     "note": "hidden HTML comment + white-on-white text"},
    {"file": "sunday-kitchen.html", "label": "Recipe blog", "task": "How long do I bake the cake?",
     "note": "instruction hidden in an image's alt text"},
    {"file": "gadget-lab.html", "label": "Product review", "task": "What does the reviewer think of the battery life?",
     "note": "promotional steering in the body text"},
]


def _log(origin: str, source: str, task: str, text: str, res: dict, url: str | None = None):
    if origin == "sample":  # the auto-run sample on the home page is not user activity
        return
    rec = {
        "id": uuid.uuid4().hex[:8],
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origin": origin, "source": source, "task": task, "url": url,
        "action": res["action"], "latency_ms": res.get("latency_ms"),
        "n_spans": len(res["spans"]),
        "injections": [{"text": v["text"][:300], "score": v["score"], "reason": v.get("reason")} for v in res["detected_spans"]],
        "excerpt": text[:240],
    }
    _activity.append(rec)
    del _activity[:-500]
    ACTIVITY_PATH.parent.mkdir(exist_ok=True)
    with open(ACTIVITY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ------------------------------------------------------------------ API
@app.get("/api/health")
def health():
    return {"ready": _state["sentinel"] is not None, "error": _state["error"]}


@app.get("/api/examples")
def examples():
    return json.load(open(APP / "examples.json"))


@app.get("/api/attacks")
def attacks():
    return json.load(open(APP / "attacks.json"))


@app.post("/api/scan")
def scan(req: ScanReq):
    s = _state["sentinel"]
    if s is None:
        return JSONResponse({"error": "model still loading"}, status_code=503)
    out = {}
    with _lock:
        for m in (["sentinel", "baseline"] if req.mode == "both" else [req.mode]):
            t0 = time.time()
            r = s.scan(req.task, req.tool_output, req.source, mode=m)
            r["latency_ms"] = round((time.time() - t0) * 1000)
            out[m] = r
    main = out.get("sentinel")
    if main:
        _log(req.origin, req.source, req.task, req.tool_output, main)
    return out


@app.get("/api/demo-pages")
def demo_pages(request: Request):
    base = f"{request.url.scheme}://{request.url.netloc}"
    return [{**d, "url": f"{base}/demo/{d['file']}"} for d in DEMO_PAGES]


@app.get("/demo/{name}")
def demo_page(name: str):
    if name not in {d["file"] for d in DEMO_PAGES}:
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(APP / "demo_pages" / name, media_type="text/html")


@app.post("/api/fetch")
def fetch(req: FetchReq):
    """Fetch a URL the way an agent's web tool would, then scan it."""
    from sentinel.webfetch import FetchError, fetch_text

    s = _state["sentinel"]
    if s is None:
        return JSONResponse({"error": "model still loading"}, status_code=503)
    try:
        page = fetch_text(req.url)
    except FetchError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    out = {"page": {k: page[k] for k in ("url", "title", "chars", "truncated")}, "text": page["text"]}
    with _lock:
        for m in (["sentinel", "baseline"] if req.mode == "both" else [req.mode]):
            t0 = time.time()
            r = s.scan(req.task, page["text"], "webpage", mode=m)
            r["latency_ms"] = round((time.time() - t0) * 1000)
            out[m] = r
    if out.get("sentinel"):
        _log(req.origin, "webpage", req.task, page["text"], out["sentinel"], url=page["url"])
    return out


class HtmlReq(BaseModel):
    html: str = Field(max_length=2_500_000)


@app.post("/api/html-to-text")
def html_to_text_api(req: HtmlReq):
    """Flatten an uploaded HTML file the way an agent's web tool would (comments and alt text kept)."""
    from sentinel.webfetch import MAX_CHARS, html_to_text

    title, text = html_to_text(req.html)
    return {"title": title, "text": text[:MAX_CHARS]}


# ------------------------------------------------------------------ benchmark: live re-run + error explorer
_bench: dict = {}


def _bench_sample() -> dict:
    if "docs" not in _bench:
        f = APP / "bench_sample.json"
        docs = json.load(open(f)) if f.exists() else []
        _bench["docs"] = {d["id"]: d for d in docs}
    return _bench["docs"]


class BenchReq(BaseModel):
    id: str = Field(max_length=64)


def _outcome(doc: dict, res: dict) -> dict:
    """Same doc-level definitions as sentinel/metrics.py: a poisoned doc is caught if any injected span is flagged;
    a harmless-command or clean doc is a false alarm if any non-injected span is flagged."""
    flagged = {(v["start"], v["end"]) for v in res["spans"] if v["verdict"] == "injection"}
    labels = {(a, b): l for a, b, l in doc["spans"]}
    hit = any(k in flagged and labels.get(k) for k in labels)
    fa = any(k in flagged and not labels.get(k) for k in labels)
    if doc["kind"] == "poisoned":
        return {"outcome": "caught" if hit else "missed", "flagged": len(flagged), "ms": res.get("latency_ms")}
    return {"outcome": "false_alarm" if fa else "passed", "flagged": len(flagged), "ms": res.get("latency_ms")}


@app.get("/api/benchmark/sample")
def bench_sample_list():
    docs = _bench_sample()
    return [{"id": d["id"], "kind": d["kind"], "family": d["family"], "source": d["source"], "origin": d["origin"]}
            for d in docs.values()]


@app.post("/api/benchmark/run")
def bench_run(req: BenchReq):
    s = _state["sentinel"]
    if s is None:
        return JSONResponse({"error": "model still loading"}, status_code=503)
    d = _bench_sample().get(req.id)
    if d is None:
        return JSONResponse({"error": "unknown document"}, status_code=404)
    out = {}
    with _lock:
        for m in ("sentinel", "baseline"):
            t0 = time.time()
            r = s.scan(d["task"], d["text"], d["source"], mode=m)
            r["latency_ms"] = round((time.time() - t0) * 1000)
            out[m] = _outcome(d, r)
    return {"id": d["id"], "kind": d["kind"], "family": d["family"], "source": d["source"], **out}


@app.get("/api/benchmark/errors")
def bench_errors():
    f = APP / "bench_errors.json"
    return json.load(open(f)) if f.exists() else JSONResponse({"error": "not exported yet"}, status_code=404)


@app.get("/api/activity")
def activity(limit: int = 200):
    return list(reversed(_activity))[:limit]


@app.get("/api/activity/export")
def activity_export():
    body = json.dumps(list(reversed(_activity)), indent=2)
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=sentinel-activity.json"})


@app.delete("/api/activity")
def activity_clear():
    _activity.clear()
    if ACTIVITY_PATH.exists():
        ACTIVITY_PATH.unlink()
    return {"cleared": True}


@app.get("/api/results")
def results():
    res = {}
    for name in ["final", "boundary"]:
        p = ROOT / "results" / f"{name}.json"
        if p.exists():
            res[name] = json.load(open(p))
    res["dataset"] = _state["dataset"] or {}
    return res


# ------------------------------------------------------------------ pages
def _page(name: str):
    return lambda: FileResponse(STATIC / name)


for path, file in [("/", "index.html"), ("/how-it-works", "how-it-works.html"), ("/attack-lab", "attack-lab.html"),
                   ("/activity", "activity.html"), ("/integrate", "integrate.html"),
                   ("/benchmark", "benchmark.html"), ("/about", "about.html")]:
    app.add_api_route(path, _page(file), methods=["GET"], include_in_schema=False)

app.mount("/static", StaticFiles(directory=STATIC), name="static")
