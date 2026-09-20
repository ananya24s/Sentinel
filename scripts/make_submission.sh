#!/usr/bin/env bash
# Build the Round 2 ZIP:   scripts/make_submission.sh [path/to/demo-video.mp4]
#   FP16=1 scripts/make_submission.sh video.mp4     # store the scorer weights in half precision (about half the size)
set -euo pipefail
cd "$(dirname "$0")/.."
VIDEO="${1:-}"
OUT=submission; NAME=BugSlayers_Sentinel_Round2
rm -rf "$OUT"; mkdir -p "$OUT/$NAME/Sentinel"
STAGE="$OUT/$NAME/Sentinel"

rsync -a \
  --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.DS_Store' --exclude 'submission' \
  --exclude 'data/raw' --exclude 'data/cache' --exclude 'data/processed' --exclude 'data/activity.jsonl' \
  --exclude 'docs/*.pptx' --exclude 'docs/*.template.md' \
  ./ "$STAGE/"

if [ "${FP16:-0}" = "1" ]; then
  echo "Converting scorer weights to fp16…"
  .venv/bin/python - <<PY
import torch
from safetensors.torch import load_file, save_file
p = "$STAGE/models/scorer/model.safetensors"
sd = {k: (v.half() if v.dtype == torch.float32 else v) for k, v in load_file(p).items()}
save_file(sd, p, metadata={"format": "pt"})
PY
fi

# top level of the ZIP: the deck, the video, a short README, and the project
cp docs/BugSlayers_Sentinel_Round2.pptx "$OUT/$NAME/" 2>/dev/null || echo "WARNING: PPT not found in docs/"
[ -n "$VIDEO" ] && cp "$VIDEO" "$OUT/$NAME/Sentinel_demo_video.${VIDEO##*.}" || echo "NOTE: no video given; add it to the ZIP folder yourself"
cat > "$OUT/$NAME/START_HERE.txt" <<TXT
Sentinel: Team Bug Slayers (Engineers' Day, LLM Engineering Challenge, Problem 5)

  BugSlayers_Sentinel_Round2.pptx   the Round 2 deck
  Sentinel_demo_video.*             the prototype demo video
  Sentinel/                         the complete working prototype and source

To run the prototype (macOS/Linux, Python 3.12):
  cd Sentinel && ./run.sh           then open http://localhost:8000
The trained models are included (models/), so nothing is downloaded and no API key is needed.
See Sentinel/README.md for the full pipeline, and Sentinel/docs/ for the demo script and Q&A notes.
TXT
(cd "$OUT" && zip -qr "$NAME.zip" "$NAME")
ls -lh "$OUT/$NAME.zip"
