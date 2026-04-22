#!/usr/bin/env python3
"""
check_sensor_health.py — 獨立診斷 CLI

讀取 state/sensor_health.json（由 run_auto_decision_scan 產生），
印出人類可讀的健康狀態報告。

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/check_sensor_health.py

Exit codes:
    0 — 正常或降級（只有輔助感測器缺失）
    0 — sensor_health.json 不存在（印 UNKNOWN 但不報錯）
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etf_core import context
from etf_core.state_io import safe_load_json


def main() -> int:
    state_dir = context.get_state_dir()
    health = safe_load_json(state_dir / "sensor_health.json", {})

    if not health:
        print("[SENSOR HEALTH] UNKNOWN — sensor_health.json 不存在或為空")
        print("請先執行一次 run_auto_decision_scan 以產生健康狀態快照")
        return 0

    checked_at = health.get("checked_at", "unknown")
    healthy = health.get("healthy", False)
    critical = health.get("critical_failures", [])
    auxiliary = health.get("auxiliary_missing", [])

    print(f"[SENSOR HEALTH] {checked_at}")

    if healthy:
        print("✅ 關鍵感測器：全部正常")
    else:
        failed = ", ".join(critical)
        print(f"🚨 關鍵感測器失效：{failed}")
        print("   → 管線已中止，不跑決策")

    if auxiliary:
        missing = ", ".join(auxiliary)
        print(f"⚠️  輔助感測器缺失：{missing}")
        print("   → 管線降級執行，risk_context_summary 已標記警示")
    else:
        print("✅ 輔助感測器：全部正常")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
