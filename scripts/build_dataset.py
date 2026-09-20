"""Build the Sentinel evaluation/training corpus from BIPIA.

BIPIA ships attack instructions grouped by *attack family*, with different
families in its train and test files. We keep that split (so the test set has
attack families the model has never seen) and carve a validation set out of the
train file (held-out families x held-out documents) for calibrating fusion.

Each document is one of:
  clean     - an untouched context
  poisoned  - context + one injected attack instruction (label 1 spans)
  benign    - context + one harmless instruction-shaped sentence (label 0)
"""
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinel import synth  # noqa: E402
from sentinel.benign import BENIGN_TEST, BENIGN_TRAIN, PREFIXES  # noqa: E402
from sentinel.segment import segment  # noqa: E402

BIPIA = ROOT / "data/raw/BIPIA/benchmark"
OUT = ROOT / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)

VAL_TEXT_FAMILIES = {"Language Translation", "Anagramming", "Persuasion"}
VAL_CODE_FAMILIES = {"Cryptocurrency Mining", "Cookie Theft"}
MAX_CTX_CHARS = 4500  # keep probe cost bounded
CODE_TASK = "Using the context, fix the bug in the code."


def load_jsonl(p):
    return [json.loads(l) for l in open(p)]


def contexts(split):
    """Yield (source, task, context_text)."""
    out = []
    for r in load_jsonl(BIPIA / f"email/{split}.jsonl"):
        # BIPIA joins the header fields with "|"; real emails (and agents' mail tools) put each on its own line
        ctx = re.sub(r"\|(?=(?:SUBJECT|EMAIL_FROM|RECEIVED DATE|CONTENT):)", "\n", r["context"])
        out.append(("email", r["question"], ctx))
    for r in load_jsonl(BIPIA / f"table/{split}.jsonl"):
        out.append(("table", r["question"], r["context"]))
    for r in load_jsonl(BIPIA / f"code/{split}.jsonl"):
        ctx = r["context"]
        ctx = "\n".join(ctx) if isinstance(ctx, list) else ctx
        out.append(("code", CODE_TASK, ctx))
    return [c for c in out if 200 <= len(c[2]) <= MAX_CTX_CHARS]


def web_contexts(rng, lo, hi):
    """News-style web pages built from AG News items (headline + several paragraphs)."""
    import re
    rows = json.load(open(ROOT / "data/raw/agnews_sample.json"))[lo:hi]
    pat = re.compile(r"^(.*?)\s+\((?:[\w .&']{2,25})\)\s+(.*)$", re.S)
    items = []
    for r in rows:
        t = r["text"].replace("\\", " ").replace("  ", " ").strip()
        m = pat.match(t)
        items.append((m.group(1).strip(), m.group(2).strip()) if m else (None, t))
    docs = []
    for i in range(0, len(items) - 4, 4):
        title = next((it[0] for it in items[i:i + 4] if it[0]), "Local News Update")
        body = [it[1] for it in items[i:i + 4]]
        docs.append(("webpage", rng.choice(synth.WEB_TASKS), title + "\n" + "\n".join(body)))
    return [d for d in docs if 250 <= len(d[2]) <= MAX_CTX_CHARS]


def _bucket(key):
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % 5


def realweb_contexts(rng):
    """Windows of real, harvested web pages. Split by site (Wikipedia by page) so test sites are never seen."""
    path = ROOT / "data/raw/webcorpus.json"
    out = {"train": [], "val": [], "cal": [], "test": []}
    if not path.exists():
        return out
    for pg in json.load(open(path)):
        key = pg["url"] if "wikipedia.org" in pg["domain"] else pg["domain"]
        b = _bucket(key)
        split = {0: "test", 1: "cal", 2: "val"}.get(b, "train")
        lines = pg["text"].split("\n")
        title = (pg["title"] or "").split("|")[0].split(" - ")[0].strip()
        for _ in range(6):
            if len(lines) < 8:
                break
            i = rng.randint(0, max(0, len(lines) - 8))
            buf, n = [], 0
            while i < len(lines) and n < rng.randint(1800, 3800):
                buf.append(lines[i]); n += len(lines[i]) + 1; i += 1
            ctx = "\n".join(buf)
            if len(ctx) < 300:
                continue
            task = (rng.choice([f"Summarize the page about {title}.", f"What is this page about?", f"Give me the key points of this page."])
                    if title and len(title) < 80 else rng.choice(synth.WEB_TASKS))
            out[split].append(("webpage", task, ctx))
    return out


def attacks(kind, split):
    d = json.load(open(BIPIA / f"{kind}_attack_{split}.json"))
    return [(fam, a) for fam, items in d.items() for a in items]


def insert(text, payload, mode, rng):
    """Insert payload; return (new_text, start, end) of the payload's char range."""
    lines = text.split("\n")
    if mode == "start":
        return payload + "\n" + text, 0, len(payload)
    if mode == "end":
        base = text.rstrip("\n") + "\n"
        return base + payload, len(base), len(base) + len(payload)
    if mode == "middle" and len(lines) > 2:
        k = rng.randint(1, len(lines) - 1)
        head = "\n".join(lines[:k]) + "\n"
        tail = "\n".join(lines[k:])
        return head + payload + "\n" + tail, len(head), len(head) + len(payload)
    # inline: append to a random line that ends a sentence (so it stays a separate sentence)
    idx = [i for i, l in enumerate(lines) if l.strip() and l.rstrip()[-1] in ".!?"]
    if not idx:
        return insert(text, payload, "end", rng)
    k = rng.choice(idx)
    head = "\n".join(lines[: k + 1])
    tail = lines[k + 1 :]
    new = head + " " + payload + ("\n" + "\n".join(tail) if tail else "")
    return new, len(head) + 1, len(head) + 1 + len(payload)


def label_spans(text, a, b):
    rows = []
    for s in segment(text):
        ov = max(0, min(s.end, b) - max(s.start, a))
        rows.append({"start": s.start, "end": s.end, "text": s.text,
                     "label": int(a is not None and ov / max(1, s.end - s.start) >= 0.5)})
    return rows


def make_doc(uid, split, source, task, ctx, kind, payload=None, family=None, rng=None):
    if kind == "clean":
        text, a, b = ctx, None, None
    else:
        mode = rng.choice(["start", "middle", "middle", "end", "inline"])
        text, a, b = insert(ctx, payload, mode, rng)
    spans = [{"start": s.start, "end": s.end, "text": s.text, "label": 0} for s in segment(text)] \
        if kind != "poisoned" else label_spans(text, a, b)
    if kind == "poisoned" and not any(s["label"] for s in spans):
        text, a, b = insert(ctx, payload, "end", rng)  # guarantee a labelled span
        spans = label_spans(text, a, b)
    return {"id": uid, "split": split, "source": source, "task": task, "kind": kind,
            "family": family, "payload": payload, "text": text, "spans": spans}


def build(split, ctxs, text_atts, code_atts, benign, n_poison, rng, synth_atts, headlines, comments=()):
    docs = []
    for i, (src, task, ctx) in enumerate(ctxs):
        docs.append(make_doc(f"{split}-{i}-c", split, src, task, ctx, "clean", rng=rng))
        for j in range(n_poison):
            if src == "code":
                fam, payload = rng.choice(code_atts)
            elif rng.random() < (0.5 if src == "webpage" else 0.3):
                fam, payload = rng.choice(synth_atts)
            else:
                fam, payload = rng.choice(text_atts)
            if src == "webpage" and "\n" not in payload and rng.random() < 0.18:
                payload = f"<!-- {payload} -->"  # hidden-in-a-comment variant
            docs.append(make_doc(f"{split}-{i}-p{j}", split, src, task, ctx, "poisoned", payload, fam, rng))
        r = rng.random()
        if src == "webpage" and r < 0.3:
            b = rng.choice(headlines)
        elif src == "webpage" and r < 0.55 and comments:
            b = rng.choice(comments)
        else:
            b = rng.choice(PREFIXES) + rng.choice(benign)
        docs.append(make_doc(f"{split}-{i}-b", split, src, task, ctx, "benign", b, "benign", rng))
    return docs


def main():
    rng = random.Random(7)
    tr_ctx = contexts("train")
    rng.shuffle(tr_ctx)
    cut = int(len(tr_ctx) * 0.8)
    # cap table docs for train to keep runtime sensible
    fit_ctx, val_ctx = tr_ctx[:cut], tr_ctx[cut:]
    te_ctx = contexts("test")

    tt_train, ct_train = attacks("text", "train"), attacks("code", "train")
    fit_text = [x for x in tt_train if x[0] not in VAL_TEXT_FAMILIES]
    val_text = [x for x in tt_train if x[0] in VAL_TEXT_FAMILIES]
    fit_code = [x for x in ct_train if x[0] not in VAL_CODE_FAMILIES]
    val_code = [x for x in ct_train if x[0] in VAL_CODE_FAMILIES]
    te_text, te_code = attacks("text", "test"), attacks("code", "test")

    fit_ctx = fit_ctx + web_contexts(rng, 0, 2400)
    val_ctx = val_ctx + web_contexts(rng, 2400, 2800)
    te_ctx = te_ctx + web_contexts(rng, 2800, 3800)
    rw = realweb_contexts(rng)  # real harvested pages, split by site
    fit_ctx, val_ctx = fit_ctx + rw["train"], val_ctx + rw["val"]
    cm = synth.BENIGN_COMMENTS
    syn_fit, syn_val, syn_te = synth.attacks("train", rng, 0), synth.attacks("val", rng, 40), synth.attacks("test", rng, 0)
    half = len(BENIGN_TRAIN) * 3 // 4
    hl = synth.HEADLINES
    sets = {
        "train": build("train", fit_ctx, fit_text, fit_code, BENIGN_TRAIN[:half], 2, rng, syn_fit, hl["train"][:14], cm["train"][:8]),
        "val": build("val", val_ctx, val_text, val_code, BENIGN_TRAIN[half:], 1, rng, syn_val, hl["train"][14:], cm["train"][8:]),
        "test": build("test", te_ctx, te_text, te_code, BENIGN_TEST, 2, rng, syn_te, hl["test"], cm["test"]),
    }
    for d in sets["train"] + sets["val"]:
        d.setdefault("origin", "bench")
    # split the test pool: a seeded random third of attack families becomes a calibration set for the
    # fusion; those families are excluded from evaluation for every system
    pool = sets.pop("test")
    fams = sorted({d["family"] for d in pool if d["kind"] == "poisoned"})
    cal_fams = set(random.Random(11).sample(fams, len(fams) // 3))
    def in_cal(d):
        if d["kind"] == "poisoned":
            return d["family"] in cal_fams
        return int(d["id"].split("-")[1]) % 3 == 0
    sets["cal"] = [d for d in pool if in_cal(d)]
    sets["test"] = [d for d in pool if not in_cal(d)]
    # real harvested pages from held-out sites join the calibration / test splits (all attack families)
    for name, key in (("cal", "calrw"), ("test", "testrw")):
        extra = build(key, rw[name], te_text, te_code, BENIGN_TEST, 2, rng, syn_te, hl["test"], cm["test"])
        for d in extra:
            d["origin"] = "realweb"
            d["split"] = name
        sets[name] += extra
    print("calibration families:", sorted(cal_fams))
    for name, docs in sets.items():
        with open(OUT / f"{name}.jsonl", "w") as f:
            for d in docs:
                f.write(json.dumps(d) + "\n")
        k = {}
        for d in docs:
            k[d["kind"]] = k.get(d["kind"], 0) + 1
        pos = sum(s["label"] for d in docs for s in d["spans"])
        tot = sum(len(d["spans"]) for d in docs)
        fams = sorted({d["family"] for d in docs if d["kind"] == "poisoned"})
        print(f"{name:5s} docs={len(docs):4d} {k} spans={tot} positive_spans={pos} families={len(fams)}")


if __name__ == "__main__":
    main()
