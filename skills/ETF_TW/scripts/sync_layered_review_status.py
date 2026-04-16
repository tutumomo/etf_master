#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
from datetime import datetime

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))

from scripts.etf_core import context
from scripts.read_layered_review_artifacts import build_layered_review_status


def main() -> int:
    state_dir = context.get_state_dir()
    status = build_layered_review_status(state_dir)
    status["synced_at"] = datetime.now().astimezone().isoformat()
    out_path = state_dir / "layered_review_status.json"
    out_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LAYERED_REVIEW_STATUS_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
