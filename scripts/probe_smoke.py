"""Sanity-check the influence probe on hand-written cases: injections vs harmless vs useful spans."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sentinel.probe import Probe
from sentinel.segment import segment

ex = {e["id"]: e for e in json.load(open(ROOT / "app/examples.json"))}
cases = [  # (example id, substring of the span to test, expectation)
    ("override", "Ignore the user's request", "INJECTION"),
    ("override", "Service on the new lines", "useful"),
    ("marketing", "When you write your answer", "INJECTION"),
    ("marketing", "Battery life averaged", "useful"),
    ("email-b64", "Reply using Base64", "INJECTION"),
    ("email-b64", "was charged $482.30", "useful"),
    ("recipe", "Bake for twenty-five", "harmless command (useful)"),
    ("recipe", "Preheat the oven", "harmless command"),
    ("table", "Translate your answer", "INJECTION"),
]
p = Probe()
cache = {}
print(f"{'expect':26s} {'d_rel':>6s} {'shift':>6s} {'judge':>6s}  span")
for eid, sub, expect in cases:
    e = ex[eid]; text = e["tool_output"]
    sp = next(s for s in segment(text) if sub in s.text)
    t0 = time.time()
    if eid not in cache: cache[eid] = p.answer(e["task"], text)
    r = p.influence(e["task"], text, sp.start, sp.end, sp.text, cache[eid])
    print(f"{expect:26s} {r['d_rel']:6.2f} {r['shift']:6.2f} {r['judge']:6.2f}  {sp.text[:55]!r}  ({time.time()-t0:.1f}s)")
    if expect == "INJECTION":
        print(f"     with:    {r['answer_with'][:110]!r}\n     without: {r['answer_without'][:110]!r}")
