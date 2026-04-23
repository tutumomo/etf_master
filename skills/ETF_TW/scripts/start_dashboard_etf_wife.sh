#!/bin/zsh
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

ROOT="$HOME/.hermes/profiles/etf_master/skills/ETF_TW"
VENV_BIN="$ROOT/.venv/bin"
HOST="127.0.0.1"
PORT="5056"
LOG_DIR="$ROOT/logs"
STARTUP_LOG="$LOG_DIR/dashboard-startup-etf_wife.log"

# Override instance routing
export AGENT_ID="etf_wife"
export OPENCLAW_AGENT_NAME="$AGENT_ID"

mkdir -p "$LOG_DIR"
cd "$ROOT"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  echo "[$(timestamp)] $*" | tee -a "$STARTUP_LOG"
}

# Check if port is already occupied by our dashboard
LISTEN_OUTPUT="$( lsof -nP -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true )"
LISTEN_LINE="$(printf '%s\n' "$LISTEN_OUTPUT" | awk 'NR==2 {print $2 "|" $1}')"
if [[ -n "$LISTEN_LINE" ]]; then
  PID="${LISTEN_LINE%%|*}"
  PROC="${LISTEN_LINE#*|}"
  CMDLINE="$(ps -p "$PID" -o command= 2>/dev/null || true)"
  if [[ "$CMDLINE" == *"uvicorn"* && "$CMDLINE" == *"dashboard.app:app"* ]]; then
    log "etf_wife dashboard already running on ${HOST}:${PORT} (pid=$PID); exiting"
    exit 0
  fi
  log "port ${PORT} occupied by pid=$PID; killing it"
  kill -9 "$PID" 2>/dev/null || true
  sleep 1
fi

log "starting etf_wife dashboard on ${HOST}:${PORT}"
exec "$VENV_BIN/uvicorn" dashboard.app:app --host "$HOST" --port "$PORT"
