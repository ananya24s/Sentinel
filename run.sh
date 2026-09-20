#!/usr/bin/env bash
# Start the Sentinel demo:  ./run.sh   (then open http://localhost:8000)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { echo "Creating virtual environment…"; python3.12 -m venv .venv; .venv/bin/pip install -q -r requirements.txt; }
# The trained models (about 500 MB) are not stored in the repository or the submission ZIP. First run: download them once.
#   SENTINEL_MODELS_ZIP=/path/to/sentinel-models.zip ./run.sh     install from a file you already have (works offline)
MODELS_URL="${SENTINEL_MODELS_URL:-https://github.com/ananya24s/Sentinel/releases/download/v1.0/sentinel-models.zip}"
if [ ! -f models/offtopic.joblib ] || [ ! -f models/scorer/model.safetensors ] || [ ! -d models/minilm ]; then
  if [ -n "${SENTINEL_MODELS_ZIP:-}" ]; then
    echo "Installing models from $SENTINEL_MODELS_ZIP …"; unzip -q -o "$SENTINEL_MODELS_ZIP" -d .
  else
    echo "Downloading the trained models (about 500 MB, one time only)…"
    curl -fL --retry 3 --progress-bar -o models.zip.part "$MODELS_URL" || {
      rm -f models.zip.part
      echo; echo "Could not download the models from $MODELS_URL"
      echo "Download sentinel-models.zip yourself, then run:  SENTINEL_MODELS_ZIP=/path/to/sentinel-models.zip ./run.sh"; exit 1; }
    unzip -q -o models.zip.part -d . && rm -f models.zip.part
  fi
  [ -f models/offtopic.joblib ] && [ -f models/scorer/model.safetensors ] || { echo "The models archive looks incomplete."; exit 1; }
fi
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"   # HOST=0.0.0.0 ./run.sh   lets teammates on the same Wi-Fi open the site
export HF_HUB_OFFLINE=1   # models are cached locally after the first run
echo "Sentinel → http://localhost:$PORT"
[ "$HOST" = "0.0.0.0" ] && echo "Teammates on this network can open → http://$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d" " -f1):$PORT"
[ -z "${NO_OPEN:-}" ] && ( sleep 6; command -v open >/dev/null && open "http://localhost:$PORT" ) &
exec .venv/bin/python -m uvicorn app.server:app --host "$HOST" --port "$PORT"
