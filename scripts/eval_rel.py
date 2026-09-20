"""Stage-A fusion: scorer confidence + off-topic features, fitted on the calibration split.

Model choice and decision threshold are picked by grouped cross-validation on the calibration set only; the
test set is touched once, at the end.
"""
import json, sys
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sentinel import baseline, relevance
from sentinel.fusion import logit
from sentinel.metrics import evaluate, summary_line
from sentinel.pipeline import SPOOF

CACHE = ROOT / "data/cache"

def load(split):
    docs = [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]
    sc = json.load(open(CACHE / f"scorer_{split}.json"))
    rel = json.load(open(CACHE / f"rel_{split}.json"))
    X, y, g, ix = [], [], [], []
    for di, (d, s, r) in enumerate(zip(docs, sc, rel)):
        for i, (p, f) in enumerate(zip(s, r)):
            X.append([logit(p)] + f + relevance.text_flags(d["spans"][i]["text"])); y.append(d["spans"][i]["label"]); g.append(di); ix.append((di, i))
    return docs, sc, np.array(X), np.array(y), np.array(g), ix

def to_scores(docs, ix, prob, thr):
    out = [[0.0] * len(d["spans"]) for d in docs]
    for (di, i), p in zip(ix, prob):
        out[di][i] = 1.0 if p >= thr else min(p, 0.49)
    for di, d in enumerate(docs):  # boundary rule
        for i, sp in enumerate(d["spans"]):
            if SPOOF.search(sp["text"]): out[di][i] = 1.0
    return out

MAX_BENIGN_FPR = 0.02  # harmless-command docs may be falsely flagged at most this often on cal (a margin: unseen templates raise it on test)

def best_thr(y, p, g=None, benign=None):
    """F1-maximising threshold, subject to the false-alarm ceiling on harmless-command documents."""
    best, thr = -1, 0.5
    for t in np.linspace(0.05, 0.99, 95):
        pred = p >= t
        if g is not None and benign:
            fl = {d for d in benign if pred[(g == d) & (y == 0)].any()}
            if len(fl) / len(benign) > MAX_BENIGN_FPR: continue
        tp, fp, fn = (pred & (y == 1)).sum(), (pred & (y == 0)).sum(), ((~pred) & (y == 1)).sum()
        f1 = 2 * tp / max(1, 2 * tp + fp + fn)
        if f1 > best: best, thr = f1, float(t)
    return best, thr

def main():
    cdocs, csc, Xc, yc, gc, cix = load("cal")
    tdocs, tsc, Xt, yt, gt, tix = load("test")
    names = ["scorer_logit", "s_task", "s_ctx", "z_ctx", "log_n", "addr_assistant", "addr_request", "is_header"]
    models = {
        "LR": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)),
        "GBM": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.08, max_iter=150, class_weight="balanced", random_state=0),
    }
    cv = {}
    benign = [i for i, d in enumerate(cdocs) if d["kind"] == "benign"]
    print("cal harmless-command docs:", len(benign))
    for name, mk in models.items():
        oof = np.zeros(len(yc))
        for tr, te in GroupKFold(5).split(Xc, yc, gc):
            oof[te] = mk().fit(Xc[tr], yc[tr]).predict_proba(Xc[te])[:, 1]
        f1, thr = best_thr(yc, oof, gc, benign)
        cv[name] = (f1, thr)
        print(f"cal CV  {name:4s} F1={f1:.3f} thr={thr:.2f}")
    pick = max(cv, key=lambda k: cv[k][0]); thr = cv[pick][1]
    print("picked", pick)
    model = models[pick]().fit(Xc, yc)
    prob = model.predict_proba(Xt)[:, 1]
    sent_scores = to_scores(tdocs, tix, prob, thr)
    res = evaluate(tdocs, sent_scores, 0.5)
    bl_scores = [baseline.score_doc(d["spans"]) for d in tdocs]
    bd_scores = [[1.0 if SPOOF.search(sp["text"]) else x for sp, x in zip(d["spans"], row)] for d, row in zip(tdocs, tsc)]
    rows = {"baseline": evaluate(tdocs, bl_scores, 0.5), "scorer": evaluate(tdocs, tsc, 0.5),
            "+boundary": evaluate(tdocs, bd_scores, 0.5)}
    for k, v in rows.items():
        print(summary_line(k, v))
    print(summary_line(f"+off-topic ({pick})", res))
    res["model"] = pick; res["cv_f1"] = cv[pick][0]; res["thr"] = thr

    # slice: real harvested web pages from sites never seen in training
    rwix = [i for i, d in enumerate(tdocs) if d.get("origin") == "realweb"]
    def sl(scores): return evaluate([tdocs[i] for i in rwix], [scores[i] for i in rwix], 0.5)
    realweb = {"baseline": sl(bl_scores), "scorer": sl(tsc), "sentinel": sl(sent_scores)}
    print("\nreal web pages (held-out sites):", len(rwix), "docs")
    for k, v in realweb.items():
        print(summary_line("  " + k, v))

    json.dump(res, open(ROOT / "results/offtopic.json", "w"), indent=1)
    (ROOT / "models").mkdir(exist_ok=True)
    joblib.dump({"model": model, "thr": thr, "names": names}, ROOT / "models/offtopic.joblib")
    llm = json.load(open(ROOT / "results/llm_probe_experiment.json"))
    final = {"baseline": rows["baseline"], "scorer": rows["scorer"], "+boundary": rows["+boundary"], "sentinel": res,
             "realweb": realweb,
             "llm_judge": llm["+judge"], "llm_influence": llm["+influence"], "llm_full": llm["sentinel (full)"]}
    json.dump(final, open(ROOT / "results/final.json", "w"), indent=1)
    print("\nfamily                                             base  scorer  sentinel")
    for f in rows["scorer"]["recall_by_family"]:
        print(f"{f:50s} {rows['baseline']['recall_by_family'][f]:5.2f} {rows['scorer']['recall_by_family'][f]:6.2f} {res['recall_by_family'][f]:6.2f}")

main()
