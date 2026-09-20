#!/usr/bin/env bash
# Start the Sentinel demo:  ./run.sh   (then open http://localhost:8000)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { echo "Creating virtual environment…"; python3.12 -m venv .venv; .venv/bin/pip install -q -r requirements.txt; }
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"   # HOST=0.0.0.0 ./run.sh   lets teammates on the same Wi-Fi open the site
export HF_HUB_OFFLINE=1   # models are cached locally after the first run
echo "Sentinel → http://localhost:$PORT"
[ "$HOST" = "0.0.0.0" ] && echo "Teammates on this network can open → http://$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d" " -f1):$PORT"
[ -z "${NO_OPEN:-}" ] && ( sleep 6; command -v open >/dev/null && open "http://localhost:$PORT" ) &
exec .venv/bin/python -m uvicorn app.server:app --host "$HOST" --port "$PORT"
