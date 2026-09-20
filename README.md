<p align="center"><img src="app/static/brand/mark.svg" width="88" alt="Sentinel logo"></p>

# Sentinel

**Tool output is data, not commands.**

Sentinel is a trust-boundary defense for LLM agents (Engineers' Day, LLM Engineering Challenge, Problem 5).
It sits between a tool and the agent, decides which spans of untrusted tool output are instructions aimed at the
agent, removes only those spans, and reports `ALLOW`, `NEUTRALIZE` or `ALERT`.

**Team Bug Slayers:** Ananya Singh, Naman Talwar, Pratham Dhyani
&nbsp;·&nbsp; [Code](https://github.com/ananya24s/Sentinel)
&nbsp;·&nbsp; [Demo video](https://drive.google.com/file/d/1dzJsXbQC6NVFM4IYfl-UCSFj3V1sVApw/view?usp=sharing)

> **Running it:** the trained models (about 640 MB) are not stored in the GitHub repository. The Round 2 submission ZIP
> includes them, so `./run.sh` works there with no downloads. From a plain clone, rebuild them with the pipeline below.

## How it works

```
trusted task + untrusted tool output
  1. boundary     trust is decided by channel, never by what the text claims; a span that forges a trusted role
                  (SYSTEM:, <|im_start|>, [INST] ...) is an injection by construction
  2. segment      sentences / lines / fenced code blocks, with exact character offsets
  3. fast scorer  DeBERTa-v3-small cross-encoder over (source + user task, span)
  4. off-task     leave-one-out coherence with MiniLM embeddings: how far is the span from the user's task and
                  from the rest of the document? (injections are off-task and off-topic by construction)
  5. verdict      gradient-boosted fusion of scorer confidence + off-task features + three cheap linguistic flags
                  (speaks to the assistant / refers to the user's request / looks like a mail header), fitted on a
                  calibration split of held-out attack families
  6. act          ALLOW / NEUTRALIZE (only the bad span is removed) / ALERT (dangerous payload or repeated attempts)
```

### What we tried and did not adopt
The original design ran a small local LLM with and without each suspicious span and checked whether its behaviour
moved off-task (`sentinel/probe.py`, `scripts/probe_features*.py`). With a 1.5B model the agent mostly ignores
injections, so the with/without responses barely differ: the behavioural features got near-zero weight in the fusion
and hurt precision (see "What we tried" in the Benchmark tab and `results/ablation.json`). The same idea, "is this
span off-task?", is measured directly and cheaply with sentence embeddings, which is what ships.

## Use it in your agent

Sentinel is a function, not a website: it sits between "the tool returned something" and "the model reads it".

```python
from sentinel import Guard

guard = Guard()                                   # loads the models once
safe = guard.clean(task="Summarize the article.", tool_output=page_text, source="webpage")
# give `safe` to your LLM instead of `page_text`

verdict = guard.check(task, page_text)            # full detail: action, detected_spans, trust_classification
```

```python
@guard.tool(source="webpage", task=lambda url, **_: current_user_request())
def fetch_page(url): ...                          # every result is cleaned before your agent sees it
```

```bash
python -m sentinel scan --task "Summarize the article." --url https://example.com/post   # CLI
curl -s localhost:8000/api/scan -H 'Content-Type: application/json' \
     -d '{"task":"Summarize the article.","tool_output":"...","source":"webpage"}'        # REST
python examples/agent_demo.py                     # a tiny agent loop using the guard
```

**Output** (matches the challenge spec): `processed_content`, `trust_classification`, `detected_spans`, `action`
(`ALLOW` / `NEUTRALIZE` / `ALERT`).

## Quick start

```bash
./run.sh          # creates the venv on first run, starts the demo, opens http://localhost:8000
```

Full pipeline from scratch:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# data: BIPIA benchmark, AG News web pages, and ~150 harvested real web pages; then build the corpus
git clone --depth 1 https://github.com/microsoft/BIPIA.git data/raw/BIPIA
python scripts/harvest_web.py            # real pages -> data/raw/webcorpus.json (needs internet)
python scripts/build_dataset.py

# train + evaluate
python scripts/train_scorer.py
python scripts/eval_baseline.py
python scripts/eval_scorer.py
python scripts/relevance_features.py cal test val
python scripts/eval_rel.py            # fits the final fusion, writes results/final.json + models/offtopic.joblib
python scripts/verify_pipeline.py     # runs the real pipeline end to end and checks it matches the table
python scripts/boundary_test.py
# optional: the LLM-probe experiments that were not adopted
python scripts/probe_features.py cal 0.0005 0.98 3 && python scripts/probe_features.py test 0.0005 0.98 3
python scripts/eval_full.py 0.0005 0.98

# demo site
python -m uvicorn app.server:app --port 8000     # then open http://localhost:8000
```

## Evaluation protocol

* Corpus built from **BIPIA** (email, table, code contexts) plus news-style web pages from AG News.
* BIPIA's attack **families in the test set never appear in training** (they are disjoint by design). A seeded
  random third of them forms a calibration split for the fusion and is excluded from the final evaluation.
* Synthetic families (overrides, forged roles, promotional steering, format demands, exfiltration) use
  **different templates and payload wording in train and test**.
* Every system is scored on the same documents: `poisoned` (one injected instruction), `clean`, and `benign`
  (a harmless instruction-shaped sentence such as "Preheat the oven…").
* Metrics: span precision / recall, false-positive rate, false alarms on harmless commands, legitimate-content
  preservation, boundary classification accuracy. See `results/`.

## Testing

```bash
./run.sh                                  # in one terminal
python scripts/e2e_check.py               # in another: every page, every endpoint, the log, the SDK and the CLI
python scripts/real_pages_check.py        # scans real public pages (no attacks in them) and lists false alarms
python scripts/attack_lab_check.py        # the Attack lab scoreboard, without the browser
```

## Acknowledgements

* **BIPIA** (Microsoft) for the indirect-prompt-injection benchmark; **AG News** for news-style web text.
* **DeBERTa-v3-small** (Microsoft) and **all-MiniLM-L6-v2** (Sentence-Transformers) as the pretrained models.
* Real public web pages were harvested only to build clean training and evaluation text; they are not redistributed
  (`data/raw/` is not part of the repository). See each project's own license for its terms.

## Layout

```
sentinel/   segmenter, baseline, scorer, off-task relevance, pipeline (+ probe: the LLM experiments)
scripts/    dataset build, training, evaluation
app/        FastAPI server + single-page demo
results/    metrics produced by the scripts above
```
