"""Command line:

    python -m sentinel scan --task "Summarize the article." --url https://example.com/post
    python -m sentinel scan --task "Find the total." --file receipt.txt --source email --json
    cat page.txt | python -m sentinel scan --task "Summarize."
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sentinel", description="Scan untrusted tool output for injected instructions.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="scan text, a file or a URL")
    sc.add_argument("--task", required=True, help="the trusted user request")
    g = sc.add_mutually_exclusive_group()
    g.add_argument("--file", help="read tool output from a file")
    g.add_argument("--url", help="fetch a web page as the tool output")
    sc.add_argument("--source", default="webpage", choices=["webpage", "email", "table", "code", "api"])
    sc.add_argument("--json", action="store_true", help="print the full JSON verdict")
    a = ap.parse_args(argv)

    if a.url:
        from .webfetch import fetch_text
        text = fetch_text(a.url)["text"]
    elif a.file:
        text = open(a.file, encoding="utf-8", errors="replace").read()
    else:
        text = sys.stdin.read()

    from .pipeline import Sentinel
    r = Sentinel().scan(a.task, text, a.source)
    if a.json:
        print(json.dumps(r, indent=2))
        return 0
    print(f"ACTION: {r['action']}    ({len(r['detected_spans'])} injection(s) in {len(r['spans'])} spans)\n")
    for v in r["detected_spans"]:
        print(f"  ✗ {v['text'][:110]!r}\n      {v['reason']}")
    print("\n--- content the agent receives " + "-" * 40)
    print(r["processed_content"])
    return 0 if r["action"] == "ALLOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
