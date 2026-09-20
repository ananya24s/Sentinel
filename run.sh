#!/usr/bin/env bash
# Start the Sentinel demo:  ./run.sh   (then open http://localhost:8000)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { echo "Creating virtual environment…"; python3.12 -m venv .venv; .venv/bin/pip install -q -r requirements.txt; }
PORT="${PORT:-8000}"
export HF_HUB_OFFLINE=1   # models are cached locally after the first run
echo "Sentinel → http://localhost:$PORT"
( sleep 6; command -v open >/dev/null && open "http://localhost:$PORT" ) &
exec .venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port "$PORT"
