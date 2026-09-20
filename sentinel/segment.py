"""Span segmentation: cut untrusted tool output into character-offset spans.

Everything downstream (baseline, scorer, probe, neutralizer) works on spans, so
removing one span never touches the rest of the document.

Rules:
  * an HTML comment (<!-- ... -->) is one atomic span, so a multi-sentence hidden instruction is removed whole
  * a fenced code block (``` ... ```) is one atomic span, together with the
    introducing sentence when the line before it ends with ':'
  * everything else is split on newlines, then into sentences
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# split a line into sentences without breaking on abbreviations too eagerly
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[`])")
_FENCE = re.compile(r"```.*?```", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)


@dataclass
class Span:
    start: int
    end: int
    text: str


def _trim(text: str, start: int, end: int) -> Span:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return Span(start, end, text[start:end])


def _plain(text: str, lo: int, hi: int, max_line_chars: int = 400) -> list[Span]:
    spans: list[Span] = []
    pos = lo
    for line in text[lo:hi].split("\n"):
        line_start = pos
        pos += len(line) + 1
        if not line.strip():
            continue
        if len(line) <= max_line_chars and not _SENT_SPLIT.search(line):
            spans.append(_trim(text, line_start, line_start + len(line)))
            continue
        cursor = 0
        for m in _SENT_SPLIT.finditer(line):
            if m.start() > cursor:
                spans.append(_trim(text, line_start + cursor, line_start + m.start()))
            cursor = m.end()
        if cursor < len(line):
            spans.append(_trim(text, line_start + cursor, line_start + len(line)))
    return spans


def segment(text: str) -> list[Span]:
    found = [(m.start(), m.end(), "fence") for m in _FENCE.finditer(text)]
    found += [(m.start(), m.end(), "comment") for m in _COMMENT.finditer(text)]
    found.sort()
    blocks: list[tuple[int, int]] = []
    for a, b, kind in found:
        prev_end = blocks[-1][1] if blocks else 0
        if a < prev_end:  # overlapping (e.g. a fence inside a comment): keep the outer block
            continue
        if kind == "fence":
            head = text[prev_end:a].rstrip(" \t\n")
            if head.endswith(":"):  # pull in the sentence that introduces the block
                a = prev_end + head.rfind("\n") + 1 if "\n" in head else prev_end
        blocks.append((a, b))
    spans: list[Span] = []
    pos = 0
    for a, b in blocks:
        spans += _plain(text, pos, a)
        spans.append(_trim(text, a, b))
        pos = b
    spans += _plain(text, pos, len(text))
    return [s for s in spans if s.text.strip()]
