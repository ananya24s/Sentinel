#!/usr/bin/env bash
# Build the Round 2 ZIP:   scripts/make_submission.sh [path/to/demo-video.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
VIDEO="${1:-}"
OUT=submission; NAME=BugSlayers_Sentinel_Round2
rm -rf "$OUT"; mkdir -p "$OUT/$NAME/Sentinel"
STAGE="$OUT/$NAME/Sentinel"

rsync -a \
  --exclude '/models' --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.DS_Store' --exclude 'submission' \
  --exclude 'data/raw' --exclude 'data/cache' --exclude 'data/processed' --exclude 'data/activity.jsonl' \
  --exclude 'docs/*.pptx' --exclude 'docs/*.template.md' \
  ./ "$STAGE/"

# the models go into a separate archive, to be attached to a GitHub Release (the portal's ZIP limit is 50 MB)
rm -f "$OUT/sentinel-models.zip"; zip -qr "$OUT/sentinel-models.zip" models -x '*.DS_Store'
echo "models archive:"; ls -lh "$OUT/sentinel-models.zip"

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
First run downloads the trained models once (about 500 MB, from the project's GitHub Release, no API key needed):
  https://github.com/ananya24s/Sentinel/releases/download/v1.0/sentinel-models.zip
If you have sentinel-models.zip already, or are offline:  SENTINEL_MODELS_ZIP=/path/to/sentinel-models.zip ./run.sh
Code: https://github.com/ananya24s/Sentinel
See Sentinel/README.md for the full pipeline, and Sentinel/docs/ for the demo script and Q&A notes.
TXT
(cd "$OUT" && zip -qr "$NAME.zip" "$NAME")
ls -lh "$OUT/$NAME.zip"
