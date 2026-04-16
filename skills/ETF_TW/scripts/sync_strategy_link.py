#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

STATE_PATH = context.get_state_dir() / "strategy_link.json"
STRATEGY_STATE_PATH = context.get_instance_dir() / "strategy_state.json"


def build_strategy_payload(raw: dict) -> dict:
    return {
        "base_strategy": raw.get("base_strategy"),
        "scenario_overlay": raw.get("scenario_overlay"),
        "updated_at": raw.get("updated_at") or datetime.now().isoformat(),
        "source": "etf_master",
        "header_format": raw.get("header_format"),
    }


def main() -> int:
    if not STRATEGY_STATE_PATH.exists():
        fallback = {
            "base_strategy": "核心累積",
            "scenario_overlay": "無",
            "updated_at": datetime.now().isoformat(),
            "source": "sync_strategy_link_fallback",
            "header_format": None,
        }
        STRATEGY_STATE_PATH.write_text(json.dumps(fallback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raw = json.loads(STRATEGY_STATE_PATH.read_text(encoding="utf-8"))
    payload = build_strategy_payload(raw)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("STRATEGY_LINK_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
