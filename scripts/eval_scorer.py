"""Score every val/test span with the fine-tuned scorer, cache the scores, report metrics."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinel.metrics import evaluate, summary_line, threshold_for_fpr  # noqa: E402
from sentinel.scorer import Scorer  # noqa: E402

CACHE = ROOT / "data/cache"
CACHE.mkdir(parents=True, exist_ok=True)


def load(split):
    return [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]


def main():
    sc = Scorer()
    docs, scores = {}, {}
    for split in ["val", "cal", "test"]:
        docs[split] = load(split)
        cache = CACHE / f"scorer_{split}.json"
        model_file = ROOT / "models/scorer/model.safetensors"
        if cache.exists() and model_file.exists() and cache.stat().st_mtime > model_file.stat().st_mtime:
            scores[split] = json.load(open(cache))  # resume: already scored with the current model
            print(f"loaded cached {split}", flush=True)
            continue
        t0 = time.time()
        out = []
        for i, d in enumerate(docs[split]):
            out.append(sc.predict(d["source"], d["task"], [s["text"] for s in d["spans"]]))
            if i % 200 == 0:
                print(f"  {split} {i}/{len(docs[split])}  {time.time() - t0:.0f}s", flush=True)
        scores[split] = out
        json.dump(out, open(cache, "w"))
        print(f"scored {split} in {time.time() - t0:.0f}s", flush=True)

    res = {}
    thr_val = threshold_for_fpr(docs["val"], scores["val"], 0.002)
    for split in ["val", "cal", "test"]:
        res[f"{split}@0.5"] = evaluate(docs[split], scores[split], 0.5)
        res[f"{split}@fpr0.2%"] = evaluate(docs[split], scores[split], thr_val)
        print(summary_line(f"scorer/{split}@0.5", res[f"{split}@0.5"]))
        print(summary_line(f"scorer/{split}@val-thr{thr_val:.3f}", res[f"{split}@fpr0.2%"]))
    for f, r in res["test@0.5"]["recall_by_family"].items():
        print(f"   {f:55s} {r:.2f}")
    json.dump(res, open(ROOT / "results/scorer.json", "w"), indent=1)


if __name__ == "__main__":
    main()
