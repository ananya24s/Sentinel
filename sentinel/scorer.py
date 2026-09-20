"""Stage 2: fast instruction-likeness scorer (DeBERTa-v3-small cross-encoder).

Input is a (source + user task, span) pair, so the model can learn both
"does this read like a command to the agent?" and "does it relate to what the
user actually asked?".
"""
from __future__ import annotations

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "scorer"
BASE = "microsoft/deberta-v3-small"


def device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def pair_text(source: str, task: str) -> str:
    return f"[{source}] {task}"


class Scorer:
    def __init__(self, path: Path | str = MODEL_DIR, dev: str | None = None):
        self.dev = dev or device()
        self.tok = AutoTokenizer.from_pretrained(str(path))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(path), dtype=torch.float32).to(self.dev).eval()

    @torch.no_grad()
    def predict(self, source: str, task: str, spans: list[str], batch_size: int = 32) -> list[float]:
        out: list[float] = []
        a = pair_text(source, task)
        for i in range(0, len(spans), batch_size):
            chunk = spans[i : i + batch_size]
            enc = self.tok([a] * len(chunk), chunk, truncation="only_second", max_length=128,
                           padding=True, pad_to_multiple_of=32, return_tensors="pt").to(self.dev)
            logits = self.model(**enc).logits
            out += torch.softmax(logits, -1)[:, 1].float().cpu().tolist()
        return out
