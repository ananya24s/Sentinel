"""Drop-in integration helpers for agent code.

    from sentinel.guard import Guard
    guard = Guard()                                   # loads the models once

    # 1) explicit: clean a tool result before the model sees it
    safe = guard.clean(task="Summarize the article.", tool_output=page_text, source="webpage")

    # 2) decorator: every result of this tool is cleaned automatically
    @guard.tool(source="webpage", task=lambda *a, **k: current_user_request())
    def fetch(url): ...

``clean`` returns only the sanitized text. ``check`` returns the full verdict (trust classification, detected
spans, action) so you can log or alert.
"""
from __future__ import annotations

import functools
import logging
from typing import Callable

from .pipeline import Sentinel

log = logging.getLogger("sentinel")


class Guard:
    def __init__(self, sentinel: Sentinel | None = None, on_alert: Callable[[dict], None] | None = None):
        self.sentinel = sentinel or Sentinel()
        self.on_alert = on_alert
        self.last: dict | None = None

    def check(self, task: str, tool_output: str, source: str = "webpage") -> dict:
        verdict = self.sentinel.scan(task, tool_output, source)
        self.last = verdict
        if verdict["action"] != "ALLOW":
            log.warning("Sentinel %s: %d instruction-like span(s) removed from %s output",
                        verdict["action"], len(verdict["detected_spans"]), source)
            if verdict["action"] == "ALERT" and self.on_alert:
                self.on_alert(verdict)
        return verdict

    def clean(self, task: str, tool_output: str, source: str = "webpage") -> str:
        return self.check(task, tool_output, source)["processed_content"]

    def tool(self, source: str = "webpage", task: str | Callable[..., str] = "Answer the user's request."):
        """Decorator: wrap a tool function that returns text so its output is cleaned before it is returned."""
        def wrap(fn):
            @functools.wraps(fn)
            def inner(*args, **kwargs):
                out = fn(*args, **kwargs)
                if not isinstance(out, str):
                    return out
                t = task(*args, **kwargs) if callable(task) else task
                return self.clean(t, out, source)
            return inner
        return wrap
