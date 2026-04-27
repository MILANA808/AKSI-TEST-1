#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  cat <<'USAGE'
Usage:
  ./scripts/run_all.sh

Starts discovered app services inside ./apps in background.
Supported auto-detection:
  - Node.js: package.json -> npm install && npm run dev || npm start
  - Python: requirements.txt -> python -m venv .venv && pip install -r requirements.txt && python app.py
  - Go: go.mod -> go run .

Logs are written to ./.logs/<app>.log
USAGE
  exit 0
fi

mkdir -p .logs
pids=()

start_node() {
  local app="$1"
  (
    cd "$app"
    npm install
    npm run dev || npm start
  ) > "../.logs/$(basename "$app").log" 2>&1 &
  pids+=("$!")
}

start_python() {
  local app="$1"
  (
    cd "$app"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    if [[ -f "app.py" ]]; then
      python app.py
    elif [[ -f "main.py" ]]; then
      python main.py
    else
      echo "No app.py/main.py entrypoint found"
      exit 1
    fi
  ) > "../.logs/$(basename "$app").log" 2>&1 &
  pids+=("$!")
}

start_go() {
  local app="$1"
  (
    cd "$app"
    go run .
  ) > "../.logs/$(basename "$app").log" 2>&1 &
  pids+=("$!")
}

for app in apps/*; do
  [[ -d "$app" ]] || continue

  if [[ -f "$app/package.json" ]]; then
    echo "[INFO] Starting Node app: $(basename "$app")"
    start_node "$app"
  elif [[ -f "$app/requirements.txt" ]]; then
    echo "[INFO] Starting Python app: $(basename "$app")"
    start_python "$app"
  elif [[ -f "$app/go.mod" ]]; then
    echo "[INFO] Starting Go app: $(basename "$app")"
    start_go "$app"
  else
    echo "[WARN] Unsupported app type: $(basename "$app")"
  fi
done

if [[ ${#pids[@]} -eq 0 ]]; then
  echo "[WARN] No runnable apps found in ./apps"
  exit 0
fi

echo "[DONE] Started ${#pids[@]} app(s). Logs in ./.logs"
echo "PIDs: ${pids[*]}"
