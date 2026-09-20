"""Fine-tune the DeBERTa-v3-small scorer on BIPIA train attacks + hard negatives."""
import json
import random
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinel import baseline  # noqa: E402
from sentinel.scorer import BASE, MODEL_DIR, device, pair_text  # noqa: E402

EPOCHS, BS, LR, SEED = 2, 16, 3e-5, 13
SOURCES = ["webpage", "email", "table", "code", "api"]
random.seed(SEED)
torch.manual_seed(SEED)


def load(split):
    return [json.loads(l) for l in open(ROOT / f"data/processed/{split}.jsonl")]


def build_examples(docs):
    seen, pos, hard, easy = set(), [], [], []
    for d in docs:
        for s in d["spans"]:
            key = (d["task"], s["text"], s["label"])
            if key in seen:
                continue
            seen.add(key)
            ex = (d["source"], d["task"], s["text"], s["label"])
            if s["label"]:
                pos.append(ex)
            elif baseline.score_span(s["text"]) > 0 or d["kind"] == "benign" and len(s["text"]) < 160:
                hard.append(ex)
            else:
                easy.append(ex)
    random.shuffle(easy)
    easy = easy[: max(3000, 4 * len(pos))]
    return pos, hard, easy


def main():
    tr = load("train")
    pos, hard, easy = build_examples(tr)
    print(f"positives={len(pos)} hard_negatives={len(hard)} easy_negatives={len(easy)}")
    data = pos + hard + easy
    random.shuffle(data)

    tok = AutoTokenizer.from_pretrained(BASE)
    dev = device()
    model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=2, dtype=torch.float32).to(dev)

    def collate(batch):
        src, task, b, y = zip(*batch)
        # hide / randomise the source label 30% of the time so the model cannot lean on it
        a = [pair_text(random.choice(SOURCES) if random.random() < 0.3 else s_, t_) for s_, t_ in zip(src, task)]
        enc = tok(list(a), list(b), truncation="only_second", max_length=128, padding=True, pad_to_multiple_of=32, return_tensors="pt")
        enc["labels"] = torch.tensor(y)
        return enc

    dl = DataLoader(data, batch_size=BS, shuffle=True, collate_fn=collate)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    steps = EPOCHS * len(dl)
    sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)

    t0, step = time.time(), 0
    model.train()
    for ep in range(EPOCHS):
        run = 0.0
        for batch in dl:
            batch = {k: v.to(dev) for k, v in batch.items()}
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sch.step()
            opt.zero_grad()
            run += loss.item()
            step += 1
            if step % 25 == 0:
                torch.mps.empty_cache()
            if step % 50 == 0:
                print(f"ep{ep} step {step}/{steps} loss {run / 50:.4f} {time.time() - t0:.0f}s", flush=True)
                run = 0.0
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tok.save_pretrained(MODEL_DIR)
    print("saved", MODEL_DIR, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
