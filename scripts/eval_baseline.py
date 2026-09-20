import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinel import baseline  # noqa: E402
from sentinel.metrics import evaluate, summary_line  # noqa: E402

res = {}
for split in ["val", "cal", "test"]:
    docs = [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]
    scores = [baseline.score_doc(d["spans"]) for d in docs]
    m = evaluate(docs, scores, 0.5)
    res[split] = m
    print(summary_line(f"baseline/{split}", m))
    if split == "test":
        for f, r in m["recall_by_family"].items():
            print(f"   {f:32s} {r:.2f}")
(ROOT / "results").mkdir(exist_ok=True)
json.dump(res, open(ROOT / "results/baseline.json", "w"), indent=1)
