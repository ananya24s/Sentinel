"""Verdict fusion: combine scorer confidence with the probe's influence features.

A tiny logistic regression whose weights are stored as plain JSON (no pickle),
fitted on the validation split - whose attack families never appear in scorer
training - so the fusion weights are calibrated on data the scorer has not seen.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FUSION_PATH = ROOT / "models" / "fusion.json"
FEATURES = ["scorer_logit", "d_rel", "shift", "judge"]


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def features(p_scorer: float, infl: dict) -> list[float]:
    return [logit(p_scorer), infl["d_rel"], infl["shift"], infl["judge"]]


class Fusion:
    def __init__(self, w=None, b=0.0, mean=None, scale=None, lo=0.05, hi=0.95, thr=0.5):
        self.w = np.array(w if w is not None else [1.0, 0, 0, 0], dtype=float)
        self.b = float(b)
        self.mean = np.array(mean if mean is not None else [0, 0, 0, 0], dtype=float)
        self.scale = np.array(scale if scale is not None else [1, 1, 1, 1], dtype=float)
        self.lo, self.hi, self.thr = lo, hi, thr

    def prob(self, x) -> float:
        z = float(((np.asarray(x) - self.mean) / self.scale) @ self.w + self.b)
        return 1 / (1 + math.exp(-z))

    def save(self, path: Path = FUSION_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        json.dump({"w": self.w.tolist(), "b": self.b, "mean": self.mean.tolist(), "scale": self.scale.tolist(),
                   "lo": self.lo, "hi": self.hi, "thr": self.thr, "features": FEATURES}, open(path, "w"), indent=1)

    @classmethod
    def load(cls, path: Path = FUSION_PATH):
        d = json.load(open(path))
        return cls(d["w"], d["b"], d["mean"], d["scale"], d["lo"], d["hi"], d["thr"])
