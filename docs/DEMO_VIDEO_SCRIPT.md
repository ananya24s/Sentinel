# Sentinel: demo video script (about 3 minutes)

You record the screen and edit; this is the shot list and the words. Read the numbers off the screen at recording
time, they are always the live results. Record at 1440×900 or larger, browser zoom 100%, dark mode, notifications off.

**Before you press record**
1. `./run.sh` and wait for the green "Models ready" dot (about 10 seconds). Use dark mode for the main take.
2. Open the Activity page and press **Clear log**, so the recording starts clean.
3. Close other tabs. Keep the browser on `http://localhost:8000`.
4. Have this file open on a second screen.

---

## 0:00 – 0:20 · Hook (Home, empty)
**Screen:** Home as it opens: empty box, the three-number strip under the headline, the faint pages at the edges. Hold for two seconds, then click the sun/moon button once and back (a one-second flip to light and dark).
**Say:** "AI agents read web pages and emails. Attackers hide instructions in them, and the agent can't tell the difference. This is Sentinel. It reads the content first, blacks out only the hidden instruction, and hands the agent everything else. On documents it has never seen, it catches [read the first number] of poisoned ones, with the baseline at [read the baseline number]."

## 0:20 – 0:55 · Use it (Home)
**Screen:** Click **Hidden HTML comment**; the box fills but nothing is scanned yet (the Scan button pulses). Press **Scan** and let the redaction bar and stamp play. Then open **Options**, choose **Side by side with baseline**, click **Harmless admin email**, then press **Scan**.
**Say:** "Here's a normal page with an instruction hidden in an HTML comment. Sentinel removes it, and only it. Now a harmless admin email full of polite commands. Sentinel passes it untouched, and the baseline raises a false alarm. Catching attacks is easy if you flag everything; the hard part is not breaking normal content."

## 0:50 – 1:15 · A real URL (Home)
**Screen:** Clear the box, paste `http://localhost:8000/demo/city-herald.html` (the hint says it's a URL), type "Summarize the article." and press **Scan**. Click **Download report** or **Copy clean text** once to show them.
**Say:** "It also fetches live pages the way an agent's web tool sees them, including hidden comments and hidden text. Two hidden instructions, one in a comment, one in invisible text. Both gone, the article intact."

## 1:15 – 1:55 · Attack lab
**Screen:** Attack lab → **Run all cases**. Let the scoreboard fill. Hover the cards slowly. Click **Details** on one attack.
**Then (10 sec):** scroll up to **Try your own**, press **Fill with a sample**, then **Add and run**. A new card appears: Sentinel removed the hidden line, the baseline missed it. Say: "And you can add your own attack here. This one is a fake account-suspended notice; the baseline misses it."
**Say:** "Twenty cases: fourteen ways attackers hide instructions, four harmless look-alikes, and two known limits that we show on purpose. Sentinel removes [read the number] of fourteen attacks and passes all four harmless pages. The baseline removes fewer and raises false alarms. Here is what we miss: an override written in French, and a couple of subtle ones, like a sales push that reads like normal page copy. English-only training data is a real limit, and we'd rather show it than hide it."

## 1:55 – 2:20 · How it works
**Screen:** How it works → step through the five stages quickly (Next stage ×4).
**Say:** "Five stages. Trust comes from the channel: only the user's request is trusted. The text is cut into spans. A small language model scores each span. Then an off-task check asks whether the span belongs on this page and to this task at all. An injection is the odd one out. The verdict removes only the spans that fail."

## 2:20 – 2:40 · It is a function, not a website
**Screen:** Integrate. Click **Hidden HTML comment**, press **Send request**. Point at the real response on the right, then scroll to **What your model receives**: left has the hidden instruction highlighted, right has it removed. Finish on the **Copy it into your code** tabs (Python, cURL, On ALERT), which are filled in with the same text.
**Say:** "For a developer this is three lines: pass in the user's task and the tool output, and give the model the cleaned text. This is the real API response. And here is what the model would read: on the left, an agent today, with the instruction inside its context; on the right, after Sentinel, the same page with only that instruction gone. The code below is generated from this exact request, so you can paste and run it. It returns the cleaned content, the trust classification, the flagged spans and an action, exactly what the challenge specifies." *(cut to Activity for two seconds)*

## 2:40 – 3:00 · Results and honesty (Benchmark)
**Screen:** Benchmark. Scroll slowly past the KPI cards, then the ablation table, then **What we tried and did not adopt**.
**Say:** "On documents the models never trained on, including real web pages from sites they never saw, Sentinel catches [read the number] of poisoned documents against [baseline] for the baseline, with far fewer false alarms. Our first idea, a behavioural test with a small language model, didn't work at that size. We measured it, dropped it, and replaced it with the off-task check that did. Sentinel, by Team Bug Slayers."

---

### Tips
- If a scan is slow the first time, do one warm-up scan before recording.
- Keep the cursor still while numbers are on screen; zoom in on the scoreboard in the edit.
- The green "Models ready" dot in the header should be visible in the first shot.
- Deep links for quick re-takes: `/#compare`, `/#ex=3` (pre-loads that example; add `&run` to scan it too, e.g. `/#ex=3&run`), `/attack-lab#run` (auto-runs every case), `/how-it-works#stage=4`, and `?theme=light` on any page.
- You can also drop a `.txt`, `.html` or `.eml` file onto the Home box; it is a nice extra shot if you have time.
- If the live URL fetch to a public site is needed on camera, check your Wi-Fi first; the three local demo pages always work offline.
