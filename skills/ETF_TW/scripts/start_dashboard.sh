#!/bin/zsh
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

ROOT="$HOME/.hermes/profiles/etf_master/skills/ETF_TW"
VENV_BIN="$ROOT/.venv/bin"
HOST="127.0.0.1"
PORT="5055"
LOG_DIR="$ROOT/logs"
STARTUP_LOG="$LOG_DIR/dashboard-startup.log"

mkdir -p "$LOG_DIR"
cd "$ROOT"

# Hermes multi-instance contract:
# - AGENT_ID is primary (required for deterministic instance routing)
# - OPENCLAW_AGENT_NAME remains legacy fallback for old scripts
export AGENT_ID="${AGENT_ID:-etf_master}"
export OPENCLAW_AGENT_NAME="${OPENCLAW_AGENT_NAME:-$AGENT_ID}"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  echo "[$(timestamp)] $*" | tee -a "$STARTUP_LOG"
}

LISTEN_OUTPUT="$({ /usr/sbin/lsof -nP -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || lsof -nP -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true; })"
LISTEN_LINE="$(printf '%s\n' "$LISTEN_OUTPUT" | awk 'NR==2 {print $2 "|" $1}')"
if [[ -n "$LISTEN_LINE" ]]; then
  PID="${LISTEN_LINE%%|*}"
  PROC="${LISTEN_LINE#*|}"
  CMDLINE="$(ps -p "$PID" -o command= 2>/dev/null || true)"
  if [[ "$CMDLINE" == *"uvicorn"* && "$CMDLINE" == *"dashboard.app:app"* && "$CMDLINE" == *"$ROOT"* ]]; then
    log "dashboard already running on ${HOST}:${PORT} (pid=$PID, proc=$PROC); treat as success"
    exit 0
  fi
  log "port ${PORT} is occupied by another process (pid=$PID, proc=$PROC)"
  log "command: ${CMDLINE}"
  exit 1
fi

log "starting ETF_TW dashboard on ${HOST}:${PORT}"
exec "$VENV_BIN/uvicorn" dashboard.app:app --host "$HOST" --port "$PORT"
