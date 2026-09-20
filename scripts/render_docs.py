"""Fill docs/QA_PREP.template.md with the real numbers from results/*.json -> docs/QA_PREP.md."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
F = json.load(open(R / "final.json"))
DS = json.load(open(R / "dataset.json"))
LAB = json.load(open(R / "attack_lab.json")) if (R / "attack_lab.json").exists() else None
pc = lambda x: f"{x * 100:.0f}%"
S, B, RW = F["sentinel"], F["baseline"], F["realweb"]
vals = {
    "FAMS": DS["test"]["families"], "TEST_DOCS": f"{DS['test']['docs']:,}", "REAL_PAGES": DS["real_pages"],
    "DOC_S": pc(S["doc_injection_recall"]), "DOC_B": pc(B["doc_injection_recall"]),
    "PREC_S": pc(S["span_precision"]), "PREC_B": pc(B["span_precision"]),
    "FA_S": pc(S["doc_fpr_benign_imperative"]), "FA_B": pc(B["doc_fpr_benign_imperative"]),
    "KEEP_S": f"{S['content_preservation'] * 100:.1f}%",
    "RW_DOC_S": pc(RW["sentinel"]["doc_injection_recall"]), "RW_PREC_S": pc(RW["sentinel"]["span_precision"]),
    "RW_PREC_B": pc(RW["baseline"]["span_precision"]),
    "RW_FA_S": pc(RW["sentinel"]["doc_fpr_benign_imperative"]), "RW_FA_B": pc(RW["baseline"]["doc_fpr_benign_imperative"]),
}
if LAB:
    vals.update(LAB_A_S=LAB["attacks"]["sentinel"], LAB_A_B=LAB["attacks"]["baseline"], LAB_A_T=LAB["attacks"]["total"],
                LAB_H_S=LAB["harmless"]["sentinel"], LAB_H_B=LAB["harmless"]["baseline"], LAB_H_T=LAB["harmless"]["total"])
text = (ROOT / "docs/QA_PREP.template.md").read_text()
for k, v in vals.items():
    text = text.replace("{" + k + "}", str(v))
(ROOT / "docs/QA_PREP.md").write_text(text)
left = [w for w in __import__("re").findall(r"\{[A-Z_]+\}", text)]
print("rendered docs/QA_PREP.md", "unfilled:" if left else "", left)
