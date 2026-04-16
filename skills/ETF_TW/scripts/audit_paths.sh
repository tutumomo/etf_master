#!/bin/bash

# Path Mixing Audit Utility (PATH-03)
# Goal: Find any simultaneous references to legacy (~/.openclaw) and active paths (~/.hermes/profiles/etf_master)
# Usage: bash skills/ETF_TW/scripts/audit_paths.sh

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LEGACY_PATH=".openclaw"
ACTIVE_ROOT_ID="etf_master"

echo "=== Path Mixing Audit (PATH-03) ==="
echo "Target: $BASE_DIR"

# Search for legacy path strings
# Exclude common non-code paths and this script itself
# We exclude __pycache__, .git, .venv, sessions, logs, cache, and instances (as it's state)
RESULTS=$(grep -rnE "$LEGACY_PATH" "$BASE_DIR" \
    --exclude-dir=".git" \
    --exclude-dir=".venv" \
    --exclude-dir="sessions" \
    --exclude-dir="logs" \
    --exclude-dir="cache" \
    --exclude-dir="__pycache__" \
    --exclude-dir="instances" \
    --exclude="audit_paths.sh" \
    --exclude="*.md" \
    --exclude="*.log" \
    --exclude="*.pyc")

if [ -z "$RESULTS" ]; then
    echo "SUCCESS: Zero results for illegal legacy paths ($LEGACY_PATH) found in code."
    exit 0
else
    echo "WARNING: Potential path mixing found!"
    echo "$RESULTS"
    exit 1
fi
