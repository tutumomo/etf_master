#!/usr/bin/env python3
"""Wrapper: run sync_decision_reviews.py from the correct directory."""
import os
import subprocess
import sys

SCRIPT_DIR = os.path.expanduser("~/.hermes/profiles/etf_master/skills/ETF_TW")
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv/bin/python")
SCRIPT = os.path.join(SCRIPT_DIR, "scripts/sync_decision_reviews.py")

os.environ.setdefault("AGENT_ID", "etf_master")
result = subprocess.run(
    [VENV_PYTHON, SCRIPT],
    cwd=SCRIPT_DIR,
    env={**os.environ, "AGENT_ID": "etf_master"},
)
sys.exit(result.returncode)