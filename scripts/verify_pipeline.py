"""Run the real Sentinel pipeline (the code the demo uses) over the test set and compare with the ablation table."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sentinel.metrics import evaluate, summary_line
from sentinel.pipeline import Sentinel

s = Sentinel()
docs = [json.loads(l) for l in open(ROOT / "data/processed/test.jsonl")]
scores, t0 = [], time.time()
for d in docs:
    r = s.scan(d["task"], d["text"], d["source"])
    key = {(v["start"], v["end"]): v["verdict"] == "injection" for v in r["spans"]}
    scores.append([1.0 if key.get((sp["start"], sp["end"])) else 0.0 for sp in d["spans"]])
m = evaluate(docs, scores, 0.5)
print(summary_line("pipeline (end to end)", m), f"  [{(time.time()-t0)/len(docs)*1000:.0f} ms/doc]")
ref = json.load(open(ROOT / "results/final.json"))["sentinel"]
print(summary_line("ablation table row", ref))
json.dump(m, open(ROOT / "results/pipeline_check.json", "w"), indent=1)
