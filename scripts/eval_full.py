"""Fit the fusion on the calibration split (held-out attack families), then produce the full ablation on the held-out test set.

usage: python scripts/eval_full.py <lo> <hi>

Rows of the ablation (all on the same test documents, whose attack families the
scorer and the fusion never saw):
  baseline            organizer-style tags + patterns
  scorer              DeBERTa scorer alone at 0.5
  +judge              scorer + probe judge on gray-zone spans
  +influence          scorer + counterfactual features (d_rel, shift) on gray-zone spans
  sentinel (full)     scorer + all probe features
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinel import baseline  # noqa: E402
from sentinel.pipeline import SPOOF  # noqa: E402
from sentinel.fusion import Fusion, logit  # noqa: E402
from sentinel.metrics import evaluate, summary_line  # noqa: E402

CACHE = ROOT / "data/cache"
VARIANTS = {
    "+judge": ["scorer_logit", "judge"],
    "+influence": ["scorer_logit", "d_rel", "shift"],
    "sentinel (full)": ["scorer_logit", "d_rel", "shift", "judge"],
}


def load(split):
    docs = [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]
    sc = json.load(open(CACHE / f"scorer_{split}.json"))
    rows = {}
    p = CACHE / f"probe_{split}.jsonl"
    if p.exists():
        for l in open(p):
            r = json.loads(l)
            rows[(r["doc"], r["i"])] = r
    return docs, sc, rows


def row_features(p, r, cols):
    allf = {"scorer_logit": logit(p), "d_rel": r["d_rel"], "shift": r["shift"], "judge": r["judge"]}
    return [allf[c] for c in cols]


def fit(docs, sc, rows, cols, lo, hi):
    X, y = [], []
    for d, s in zip(docs, sc):
        for i, p in enumerate(s):
            r = rows.get((d["id"], i))
            if r is not None and lo <= p < hi:
                X.append(row_features(p, r, cols))
                y.append(d["spans"][i]["label"])
    X, y = np.array(X), np.array(y)
    mean, scale = X.mean(0), X.std(0) + 1e-6
    lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000).fit((X - mean) / scale, y)
    # choose decision threshold on validation gray spans by F1
    pr = lr.predict_proba((X - mean) / scale)[:, 1]
    best, thr = -1, 0.5
    for t in np.linspace(0.1, 0.9, 81):
        pred = pr >= t
        tp, fp, fn = (pred & (y == 1)).sum(), (pred & (y == 0)).sum(), ((~pred) & (y == 1)).sum()
        f1 = 2 * tp / max(1, 2 * tp + fp + fn)
        if f1 > best:
            best, thr = f1, float(t)
    return lr, mean, scale, thr, len(y), int(y.sum())


def fused_scores(docs, sc, rows, cols, model, lo, hi):
    lr, mean, scale, thr = model
    out = []
    for d, s in zip(docs, sc):
        row = []
        for i, p in enumerate(s):
            r = rows.get((d["id"], i))
            if p >= hi:
                row.append(max(p, 0.5))
            elif r is not None and lo <= p < hi:
                q = lr.predict_proba(((np.array(row_features(p, r, cols)) - mean) / scale)[None])[0, 1]
                row.append(1.0 if q >= thr else min(q, 0.49))
            else:
                row.append(p if p >= 0.5 else min(p, 0.49))
        out.append(row)
    return out


def with_boundary(docs, scores):
    """Boundary rule: a span that impersonates a trusted role is an injection by construction."""
    return [[1.0 if SPOOF.search(sp["text"]) else x for sp, x in zip(d["spans"], row)] for d, row in zip(docs, scores)]


def main():
    lo, hi = float(sys.argv[1]), float(sys.argv[2])
    vdocs, vsc, vrows = load("cal")
    tdocs, tsc, trows = load("test")
    res, table = {}, []

    m = evaluate(tdocs, [baseline.score_doc(d["spans"]) for d in tdocs], 0.5)
    res["baseline"] = m
    table.append(("baseline (tags+patterns)", m))
    m = evaluate(tdocs, tsc, 0.5)
    res["scorer"] = m
    table.append(("scorer only", m))
    m = evaluate(tdocs, with_boundary(tdocs, tsc), 0.5)
    res["+boundary"] = m
    table.append(("+boundary rule", m))

    for name, cols in VARIANTS.items():
        lr, mean, scale, thr, n, npos = fit(vdocs, vsc, vrows, cols, lo, hi)
        s = with_boundary(tdocs, fused_scores(tdocs, tsc, trows, cols, (lr, mean, scale, thr), lo, hi))
        m = evaluate(tdocs, s, 0.5)
        m["fusion_fit"] = {"val_gray_spans": n, "val_gray_positives": npos, "thr": thr,
                           "coef": dict(zip(cols, lr.coef_[0].round(3).tolist()))}
        res[name] = m
        table.append((name, m))
        if name == "sentinel (full)":
            fu = Fusion(lr.coef_[0].tolist(), float(lr.intercept_[0]), mean.tolist(), scale.tolist(), lo, hi, thr)
            fu.w = np.array(lr.coef_[0])
            # store as the 4-feature fusion used at runtime
            fu.save()

    for n, m in table:
        print(summary_line(n, m))
    print("\nrecall by held-out family (test):")
    fams = sorted(res["scorer"]["recall_by_family"])
    print(f"{'family':50s} {'base':>5s} {'scorer':>6s} {'full':>5s}")
    for f in fams:
        print(f"{f:50s} {res['baseline']['recall_by_family'][f]:5.2f} {res['scorer']['recall_by_family'][f]:6.2f} "
              f"{res['sentinel (full)']['recall_by_family'][f]:5.2f}")
    json.dump(res, open(ROOT / "results/ablation.json", "w"), indent=1)
    print("val gray:", res["sentinel (full)"]["fusion_fit"])


if __name__ == "__main__":
    main()
