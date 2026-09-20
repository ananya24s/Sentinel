"""Run the counterfactual influence test on the scorer's gray-zone spans and cache the features.

usage: python scripts/probe_features.py <val|test> <lo> <hi> <max_probe_per_doc>
Resumable: rows already in data/cache/probe_<split>.jsonl are skipped.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinel.probe import Probe  # noqa: E402

CACHE = ROOT / "data/cache"


def main():
    split, lo, hi, K = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
    docs = [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]
    scores = json.load(open(CACHE / f"scorer_{split}.json"))
    out_path = CACHE / f"probe_{split}.jsonl"
    done = set()
    if out_path.exists():
        for l in open(out_path):
            r = json.loads(l)
            done.add((r["doc"], r["i"]))

    jobs = []
    for d, sc in zip(docs, scores):
        gray = sorted([i for i, p in enumerate(sc) if lo <= p < hi], key=lambda i: -sc[i])[:K]
        if gray:
            jobs.append((d, gray))
    print(f"{split}: {len(jobs)} docs with gray spans, {sum(len(g) for _, g in jobs)} spans", flush=True)

    probe = Probe()
    t0 = time.time()
    with open(out_path, "a") as f:
        for n, (d, gray) in enumerate(jobs):
            todo = [i for i in gray if (d["id"], i) not in done]
            if not todo:
                continue
            A = probe.answer(d["task"], d["text"])
            for i in todo:
                s = d["spans"][i]
                r = probe.influence(d["task"], d["text"], s["start"], s["end"], s["text"], A)
                f.write(json.dumps({"doc": d["id"], "i": i, **r}) + "\n")
            f.flush()
            if n % 10 == 0:
                print(f"{n}/{len(jobs)} docs  {time.time() - t0:.0f}s", flush=True)
    print("done", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
