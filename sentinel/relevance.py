"""Off-task / off-topic signal: how coherent is a span with the user's task and with the rest of the document?

An injected instruction is, by construction, not about what the user asked and not about what the document
is about. We measure that with a small sentence-embedding model (MiniLM, ~22M parameters, milliseconds per doc):

  s_task   cosine(span, user task)
  s_ctx    cosine(span, centroid of every *other* span in the document)  - topical coherence
  z_ctx    s_ctx standardised within the document                        - is this the odd one out?
  n        log number of spans
"""
from __future__ import annotations

import numpy as np

from pathlib import Path

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LOCAL = Path(__file__).resolve().parents[1] / "models" / "minilm"   # bundled copy: lets Sentinel run fully offline
_model = None


def _get():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(str(LOCAL) if LOCAL.exists() else MODEL)
    return _model


def features(task: str, spans: list[str]) -> np.ndarray:
    """Return an array [n_spans, 4]: s_task, s_ctx, z_ctx, log_n."""
    n = len(spans)
    if n == 0:
        return np.zeros((0, 4))
    m = _get()
    E = m.encode(spans + [task], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    S, t = E[:-1], E[-1]
    s_task = S @ t
    if n > 1:
        tot = S.sum(0)
        C = (tot[None] - S) / (n - 1)
        C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
        s_ctx = (S * C).sum(1)
    else:
        s_ctx = np.full(n, 0.5)
    z = (s_ctx - s_ctx.mean()) / (s_ctx.std() + 1e-6)
    return np.stack([s_task, s_ctx, z, np.full(n, np.log(n + 1))], 1)
