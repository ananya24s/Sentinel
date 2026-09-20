"""Export the two files behind the Benchmark page's "Re-run it live" and "Error explorer" sections.

    python scripts/export_benchmark.py          # ~6 minutes: runs the real pipeline over the whole test set

Writes
  app/bench_sample.json   120 held-out test documents (60 poisoned, 30 harmless-command, 30 clean), drawn at random
                          with a fixed seed, with their span labels, so the page can re-run them live.
  app/bench_errors.json   every miss and false alarm the final model makes on the test set (counts), plus up to 24
                          examples of each, spread across attack families.
Both are read-only views of the held-out test split; nothing here is used for training or for choosing a threshold.
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sentinel.pipeline import Sentinel  # noqa: E402

SEED, N_SHOW = 7, 24
SAMPLE = {"poisoned": 60, "benign": 30, "clean": 30}


def spread(items, k, rng):
    """Pick up to k items, taking one per family in turn so no family dominates."""
    groups = defaultdict(list)
    for it in items:
        groups[it["family"] or it["origin"] or it["source"]].append(it)
    for g in groups.values():
        rng.shuffle(g)
    order = list(groups)
    rng.shuffle(order)
    out = []
    while len(out) < k and any(groups.values()):
        for f in order:
            if groups[f] and len(out) < k:
                out.append(groups[f].pop())
    return out


def main():
    s = Sentinel()
    docs = [json.loads(l) for l in open(ROOT / "data/processed/test.jsonl")]
    rec = []
    for i, d in enumerate(docs):
        r = s.scan(d["task"], d["text"], d["source"])
        flag = {(v["start"], v["end"]): v for v in r["spans"] if v["verdict"] == "injection"}
        score = {(v["start"], v["end"]): v["score"] for v in r["spans"]}
        flags = [(sp["start"], sp["end"]) in flag for sp in d["spans"]]
        hit = any(f and sp["label"] for f, sp in zip(flags, d["spans"]))
        fa = [sp for f, sp in zip(flags, d["spans"]) if f and not sp["label"]]
        atk = [score.get((sp["start"], sp["end"]), 0) for sp in d["spans"] if sp["label"]]
        rec.append({"d": d, "hit": hit, "fa": fa, "atk_score": max(atk) if atk else None})
        if i % 200 == 0:
            print(i, "/", len(docs), flush=True)

    def brief(x, extra):
        d = x["d"]
        return {"id": d["id"], "kind": d["kind"], "family": d["family"], "origin": d.get("origin"), "source": d["source"],
                "task": d["task"], "text": d["text"], **extra}

    rng = random.Random(SEED)
    misses = [brief(x, {"payload": x["d"]["payload"], "score": round(x["atk_score"], 3) if x["atk_score"] is not None else None})
              for x in rec if x["d"]["kind"] == "poisoned" and not x["hit"]]
    alarms = [brief(x, {"flagged": [sp["text"][:300] for sp in x["fa"]]})
              for x in rec if x["d"]["kind"] != "poisoned" and x["fa"]]
    tot = {"poisoned": sum(x["d"]["kind"] == "poisoned" for x in rec), "harmless": sum(x["d"]["kind"] != "poisoned" for x in rec)}
    errors = {"thr": json.load(open(ROOT / "results/final.json"))["sentinel"].get("thr"),
              "test_docs": len(rec), "poisoned_docs": tot["poisoned"], "harmless_docs": tot["harmless"],
              "n_misses": len(misses), "n_false_alarms": len(alarms),
              "misses": spread(misses, N_SHOW, rng), "false_alarms": spread(alarms, N_SHOW, rng)}
    json.dump(errors, open(ROOT / "app/bench_errors.json", "w"), indent=1)

    by_kind = defaultdict(list)
    for x in rec:
        by_kind[x["d"]["kind"]].append(x)
    sample = []
    for kind, n in SAMPLE.items():
        for x in rng.sample(by_kind[kind], n):
            d = x["d"]
            sample.append({"id": d["id"], "kind": kind, "family": d["family"], "origin": d.get("origin"), "source": d["source"],
                           "task": d["task"], "text": d["text"], "payload": d["payload"],
                           "spans": [[sp["start"], sp["end"], sp["label"]] for sp in d["spans"]],
                           "offline": {"hit": x["hit"], "false_alarm": bool(x["fa"])}})
    rng.shuffle(sample)
    json.dump(sample, open(ROOT / "app/bench_sample.json", "w"))
    print(f"misses {len(misses)}/{tot['poisoned']}  false alarms {len(alarms)}/{tot['harmless']}  sample {len(sample)} docs")
    print("sample offline: caught", sum(x['offline']['hit'] for x in sample if x['kind'] == 'poisoned'), "/ 60;",
          "false alarms", sum(x['offline']['false_alarm'] for x in sample if x['kind'] != 'poisoned'), "/ 60")


if __name__ == "__main__":
    main()
