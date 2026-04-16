#!/usr/bin/env python3
"""
Hermes-safe placeholder for legacy family evolution sync.

This script previously copied prompt/memory/config artifacts across older multi-agent
layouts. In the current Hermes setup, that behavior is disabled by default to
avoid cross-instance contamination and path leakage into historical directories.
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("ETF_Evolution")


def sync_evolution() -> int:
    logger.warning("sync_agent_evolution.py is disabled in Hermes mode; no files were copied.")
    logger.warning("Reason: legacy family-instance propagation is not a valid Hermes default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync_evolution())
