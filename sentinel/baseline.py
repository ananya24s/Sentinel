"""Organizer-style baseline: context-boundary tagging + deterministic patterns.

This is the thing Sentinel has to beat. It is written to be a *fair* baseline,
not a strawman: an override-phrase list plus an imperative/question detector,
which is what "deterministic instruction-pattern detection" means in practice.
"""
from __future__ import annotations

import re

OVERRIDE = re.compile(
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(previous|prior|above|earlier|all|any|the user|your)\b"
    r"|\bnew instructions?\b|\bsystem prompt\b|\byou are now\b|\bdo not follow\b|\binstead\b.{0,30}\b(do|write|reply|answer)\b",
    re.I,
)

IMPERATIVE_VERBS = (
    "write|explain|translate|provide|tell|show|list|describe|give|create|generate|summari[sz]e|reply|respond|answer|"
    "add|include|insert|ensure|make sure|use|print|output|say|repeat|convert|encode|decode|append|send|forward|"
    "share|recommend|suggest|compose|draft|calculate|find|identify|analy[sz]e|compare|predict|develop|design|"
    "incorporate|embed|feature|implement|run|execute|download|visit|click|ask"
)
IMPERATIVE = re.compile(rf"^\s*(please\s+)?({IMPERATIVE_VERBS})\b", re.I)
QUESTION = re.compile(r"^\s*(what|who|why|how|when|where|which|can you|could you|would you|do you|is there|are there)\b.*\?\s*$", re.I)
ADDRESSED = re.compile(r"\b(you must|you should|you need to|your response|in your (answer|reply|response)|the assistant|the ai)\b", re.I)


def score_span(text: str) -> float:
    """Return 1.0 if any deterministic rule fires, else 0.0."""
    t = text.strip()
    if OVERRIDE.search(t) or ADDRESSED.search(t):
        return 1.0
    if IMPERATIVE.search(t) or QUESTION.search(t):
        return 1.0
    return 0.0


def score_doc(spans) -> list[float]:
    return [score_span(s["text"]) for s in spans]
