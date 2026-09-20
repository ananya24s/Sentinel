"""Sentinel end-to-end: boundary -> segment -> score -> off-task check -> verdict -> action.

    from sentinel.pipeline import Sentinel
    s = Sentinel()
    out = s.scan(task="Summarize the article.", tool_output=page_text, source="webpage")

Stages
  1 boundary    trust comes from the channel; a span that forges a trusted role is an injection by construction
  2 scorer      DeBERTa-v3-small cross-encoder over (source + user task, span)
  3 off-task    leave-one-out coherence: how far is the span from the user's task and from the rest of the
                document (MiniLM embeddings)
  4 verdict     gradient-boosted fusion of the scorer confidence and the off-task features
  5 action      ALLOW / NEUTRALIZE / ALERT
"""
from __future__ import annotations

import re
from pathlib import Path

import joblib
import numpy as np

from . import baseline, relevance
from .fusion import logit
from .segment import segment

ROOT = Path(__file__).resolve().parents[1]
REDACTION = "[untrusted instruction removed]"

# Role / delimiter markers an attacker can paste to impersonate a trusted channel.
SPOOF = re.compile(
    r"(<\|im_start\|>\s*(system|user|assistant)|\[/?INST\]|<</?SYS>>|\b(system|assistant)\s*:(?=\s)|###\s*(system|instruction)s?\b)",
    re.I,
)
# Content that makes an injection dangerous rather than merely off-topic.
RISKY = re.compile(
    r"(system prompt|password|credential|api[_ -]?key|secret|token|https?://|\bsend\b.*\b(to|at)\b|exfiltrat|"
    r"base64|\bcurl\b|\bwget\b|rm\s+-rf|os\.system|subprocess|socket\.|\.cookies?|keylog|ransom|delete all|"
    r"credit card|email the|upload)",
    re.I,
)


class Sentinel:
    def __init__(self, scorer=None, offtopic_path: Path | None = None):
        from .scorer import Scorer

        self.scorer = scorer or Scorer()
        blob = joblib.load(offtopic_path or ROOT / "models" / "offtopic.joblib")
        self.gbm, self.thr = blob["model"], float(blob["thr"])
        relevance._get()  # load the embedding model now, not on the first scan

    # ------------------------------------------------------------------ boundary
    @staticmethod
    def boundary(trusted_instruction: str, tool_output: str, source: str) -> dict:
        """Trust is decided by *channel*, never by what the text says about itself."""
        spoofs = [m.group(0).strip() for m in SPOOF.finditer(tool_output)]
        return {
            "trusted_instruction": "trusted",
            "tool_output": "untrusted",
            "source": source,
            "spoofed_role_markers": spoofs,
        }

    # ---------------------------------------------------------------------- scan
    def scan(self, task: str, tool_output: str, source: str = "webpage", mode: str = "sentinel") -> dict:
        spans = segment(tool_output)
        texts = [s.text for s in spans]
        verdicts = []

        if mode == "baseline":
            for sp in spans:
                hit = baseline.score_span(sp.text) >= 0.5
                verdicts.append({"start": sp.start, "end": sp.end, "text": sp.text, "score": float(hit),
                                 "stage": "patterns", "verdict": "injection" if hit else "data",
                                 "reason": "matched a fixed instruction pattern" if hit else None})
        elif texts:
            p = self.scorer.predict(source, task, texts)
            F = relevance.features(task, texts)
            X = np.array([[logit(pi)] + list(fi) for pi, fi in zip(p, F)])
            q = self.gbm.predict_proba(X)[:, 1]
            for sp, pi, fi, qi in zip(spans, p, F, q):
                v = {"start": sp.start, "end": sp.end, "text": sp.text, "score": round(float(qi), 4),
                     "stage": "scorer + off-task", "verdict": "data", "reason": None,
                     "signals": {"instruction_likeness": round(float(pi), 4), "task_relatedness": round(float(fi[0]), 3),
                                 "page_coherence": round(float(fi[1]), 3), "oddness_z": round(float(fi[2]), 2)}}
                if SPOOF.search(sp.text):
                    v.update(stage="boundary", score=1.0, verdict="injection",
                             reason="impersonates a trusted role (forged system / assistant marker)")
                elif qi >= self.thr:
                    v["verdict"] = "injection"
                    v["reason"] = self._reason(pi, fi)
                verdicts.append(v)

        inj = [v for v in verdicts if v["verdict"] == "injection"]
        risky = [v for v in inj if RISKY.search(v["text"])]
        if not inj:
            action = "ALLOW"
        elif risky or len(inj) >= 2:
            action = "ALERT"  # dangerous payload (secrets, exfiltration, code) or repeated attempts
        else:
            action = "NEUTRALIZE"

        return {
            "trust_classification": self.boundary(task, tool_output, source),
            "spans": verdicts,
            "detected_spans": inj,
            "processed_content": self._neutralize(tool_output, inj),
            "action": action,
            "mode": mode,
        }

    @staticmethod
    def _reason(p: float, f) -> str:
        why = []
        if p >= 0.5:
            why.append("reads as an instruction aimed at the agent")
        if f[2] < -0.8:
            why.append("is the odd one out on this page")
        if f[0] < 0.12:
            why.append("has nothing to do with the user's task")
        return " · ".join(why) if why else "combined instruction and off-task signals"

    @staticmethod
    def _neutralize(text: str, injected: list[dict]) -> str:
        out, cursor = [], 0
        for v in sorted(injected, key=lambda x: x["start"]):
            if v["start"] < cursor:
                continue
            out.append(text[cursor : v["start"]])
            out.append(REDACTION)
            cursor = v["end"]
        out.append(text[cursor:])
        return SPOOF.sub("[role marker removed]", "".join(out))
