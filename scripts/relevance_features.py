"""Cache off-topic features for every span of val / cal / test."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sentinel import relevance

CACHE = ROOT / "data/cache"
for split in sys.argv[1:] or ["val", "cal", "test"]:
    docs = [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]
    t0 = time.time()
    out = [relevance.features(d["task"], [s["text"] for s in d["spans"]]).tolist() for d in docs]
    json.dump(out, open(CACHE / f"rel_{split}.json", "w"))
    print(split, len(docs), f"{time.time() - t0:.0f}s", flush=True)
