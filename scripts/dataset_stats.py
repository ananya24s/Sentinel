"""Write results/dataset.json: document / attack-family counts per split (read by the site and the deck)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
stats = {}
for split in ["train", "val", "cal", "test"]:
    p = ROOT / "data/processed" / f"{split}.jsonl"
    if not p.exists():
        continue
    n = poisoned = spans = realweb = 0
    fams = set()
    for line in open(p):
        d = json.loads(line)
        n += 1
        spans += len(d["spans"])
        realweb += d.get("origin") == "realweb"
        if d["kind"] == "poisoned":
            poisoned += 1
            fams.add(d["family"])
    stats[split] = {"docs": n, "poisoned": poisoned, "families": len(fams), "spans": spans, "realweb_docs": realweb}
pages = ROOT / "data/raw/webcorpus.json"
stats["real_pages"] = len(json.load(open(pages))) if pages.exists() else 0
json.dump(stats, open(ROOT / "results/dataset.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
