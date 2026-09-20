"""A minimal agent loop showing exactly where Sentinel sits.

    python examples/agent_demo.py
    python examples/agent_demo.py --url https://en.wikipedia.org/wiki/Sourdough --task "How do I make sourdough?"

The demo server must be running for the default (local demo page): ./run.sh
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel import Guard  # noqa: E402
from sentinel.webfetch import fetch_text  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000/demo/city-herald.html")
ap.add_argument("--task", default="Summarize the article.")
a = ap.parse_args()

guard = Guard(on_alert=lambda v: print(f"\n[!] ALERT raised: {len(v['detected_spans'])} injection(s) detected"))


@guard.tool(source="webpage", task=lambda url, **_: a.task)   # every result is cleaned before the agent sees it
def web_tool(url: str) -> str:
    return fetch_text(url, allow_private=True)["text"]


print(f"User asks : {a.task!r}")
print(f"Agent calls web_tool({a.url!r})\n")
context = web_tool(a.url)                       # <- what the model would read
verdict = guard.last

print("=" * 72 + "\nWHAT THE MODEL READS (Sentinel-cleaned)\n" + "=" * 72)
print(context[:1200])
print("\n" + "=" * 72 + "\nWHAT SENTINEL FOUND\n" + "=" * 72)
print(f"action: {verdict['action']}")
for v in verdict["detected_spans"]:
    print(f"  ✗ {v['text'][:100]!r}\n      why: {v['reason']}")
if not verdict["detected_spans"]:
    print("  nothing suspicious; content passed through unchanged")
