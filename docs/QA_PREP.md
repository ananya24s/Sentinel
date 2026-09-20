# Sentinel: Q&A prep

Numbers below are filled in from `results/*.json` by `scripts/render_docs.py`. Short answers first; say the bold part, add detail only if asked.

## The idea

**1. What is your innovation, in one sentence?**
**We judge a span by whether it belongs, not by how it sounds:** an injection is off-task and off-topic by construction, so we measure how far each span sits from the user's task and from the rest of the page, and combine that with a fast language-model scorer, a trust-by-channel rule and span-level removal.

**2. Your Round 1 idea was a behavioural test with a small LLM. Why isn't it in the final system?**
**We tested it and it didn't work at the size we can run locally.** A 1.5B model mostly ignores injections, so its answers with and without a span barely differ. The features got near-zero weight and precision fell. That is on the Benchmark page under "What we tried and did not adopt." The same intuition, "is this span off-task?", is measured directly with sentence embeddings, and that was the biggest gain in our ablation. We'd rather report a negative result than defend a claim the data doesn't support.

**3. Isn't an embedding similarity just topic matching? What stops it flagging a legitimate off-topic sentence?**
**It is only one input.** The fusion also uses the scorer's "reads like a command to an AI" probability, and a sentence has to look like an instruction *and* be off-task to be removed. A harmless sentence that is off-topic (a byline, a footer) doesn't read like an instruction; a command that is on-topic (a recipe step) isn't off-task. Both are in our test set as "harmless commands."

## Evidence

**4. How do you know it generalises and you didn't overfit?**
**Two hold-outs.** Whole attack families never appear in training (the test set has 29 of them), and for real web pages the *sites* are held out too, so test pages come from domains the models never saw. A seeded random third of the families was carved out for calibrating the fusion and excluded from evaluation. The test set was scored once, after the model and threshold were chosen by cross-validation on the calibration split.

**5. Give me the headline numbers.**
**On 1,749 held-out documents Sentinel catches 87% of poisoned documents versus 49% for the baseline, with precision 94% versus 43%.** On real web pages alone, from sites never seen in training: 86% caught, precision 98% versus 21% for the baseline, and harmless-command false alarms 1% versus 42%.

**6. What about false positives? Anyone can catch attacks by flagging everything.**
**We score that directly.** "False alarms on harmless commands" is the share of documents containing a normal instruction-shaped sentence (a recipe step, an admin email, an HTML comment) where something harmless was flagged: 3% for Sentinel versus 18% for the baseline. Content preserved is 99.8%. The Attack lab includes four harmless look-alikes; Sentinel passes 4 of 4, the baseline 2.

**7. Is your baseline a strawman?**
**No, but it is our implementation of what the brief describes:** boundary tagging plus deterministic instruction patterns (override phrases, imperative and question detectors, second-person address). It is reasonably strong on classic overrides and weak on reworded or hidden attacks, which is the point of the comparison. All of it is in `sentinel/baseline.py`.

**8. Did you use the recommended datasets?**
**BIPIA, yes.** We did not use AgentDojo because it needs a full running agent; instead we built a real-web evaluation by harvesting 146 public pages and inserting attacks, split by site. That is a gap and we say so.

## Robustness and limits

**9. What if the attacker knows how Sentinel works?**
**We have not run an adaptive attack against it, and we don't claim robustness to one.** Our attack families are held out from training, which tests unseen phrasing, not an adversary optimising against our threshold. A red-team loop is the first thing we'd add.

**10. What are its known failures?**
**English only; question-shaped text; attack styles far from anything we trained on.** The Attack lab shows an override in French as a known limit, and Sentinel also misses two of the fourteen attacks: a subtle hidden sales push, and one reworded override that scores just under the threshold. The decision threshold was picked on the calibration split with a ceiling of 2% false alarms on harmless-command documents; we chose that ceiling after seeing the threshold curve, so treat it as a design choice, not a blind result. We list limitations on the About page and the last slide.

**11. Why not just ask a big LLM to judge each span?**
**Cost, latency, privacy and self-attack.** A judge LLM reading untrusted text can itself be injected. We did test a small local LLM as a verifier: it added a little recall but raised false alarms, so it didn't make the final system.

**12. Does removing a span change the meaning of what's left?**
**We remove one span and leave every other word verbatim,** so content preservation is 99.8%. The removed span is replaced by a visible marker, so the agent (and a human reading the log) can see something was there.

**13. What about attacks that aren't instructions, like misinformation in a page?**
**Out of scope.** Sentinel targets indirect prompt injection: text that tries to steer the agent. Factual poisoning needs different defenses.

## Engineering

**14. How does an agent developer use it?**
**Three lines.** `Guard().clean(task, tool_output)` returns the sanitised text; `guard.check` returns the full verdict; a decorator wraps any tool. There is also a REST API and a command line. The Integrate page shows the live request and response.

**15. How fast is it?**
**About a fifth of a second per document on a laptop,** no API calls; typical pages are a few tens of milliseconds. It runs fully offline.

**16. Why a gradient-boosted fusion?**
**We compared logistic regression and gradient boosting by grouped cross-validation on the calibration split and picked the better one before touching the test set.** Gradient boosting won (CV F1 in `results/offtopic.json`).

**17. What do ALLOW, NEUTRALIZE and ALERT mean?**
**ALLOW: nothing found. NEUTRALIZE: one injection removed, rest intact. ALERT: a dangerous payload (secrets, exfiltration, code, URLs) or several attempts,** which a real deployment would escalate to a human.

**18. Boundary accuracy is 100%. Suspicious?**
**It's a structural rule, and the test is small.** Trust comes from the channel (user vs tool), so channel labelling is trivially right; the interesting part is that forged role markers are detected and stripped. It is 16 hand-written cases and we say so on the Benchmark page.

## What's yours

**19. What did you build versus reuse?**
**Reused:** the BIPIA benchmark (Microsoft), AG News, and the pretrained DeBERTa-v3-small and MiniLM models. **Ours:** the segmentation, the boundary rule, the off-task features and fusion, the training and evaluation pipeline, the real-web corpus and held-out protocol, the baseline implementation, the Attack lab cases, the SDK, CLI, API and the website.

**20. What would you do with another week?**
**Multilingual data and an evaluation slice; an adaptive red-team loop; a larger local verifier for the uncertain middle band; adapters for agent frameworks and MCP servers.**
