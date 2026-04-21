#!/usr/bin/env python3
"""
auto_calibrate_thresholds.py — CALIBRATE-01

三層機制：
1. 建議式 (suggestion)：計算各 chain 的建議門檻調整，寫入 calibration_suggestion.json
2. 硬閾值觸發 (auto-apply)：rule_engine win_rate < 40% 且樣本 >= MIN_SAMPLES 時自動套用
3. Audit trail：每次執行（含無動作）append 到 calibration_audit.jsonl

由 generate_decision_quality_weekly.py 週報流程末尾呼叫，或手動執行。

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/auto_calibrate_thresholds.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core import context
from etf_core.state_io import safe_load_json, atomic_save_json, safe_append_jsonl

TW_TZ = ZoneInfo("Asia/Taipei")

# 各 risk_temperature 的預設門檻（與 run_auto_decision_scan.BUY_THRESHOLD_BY_RISK 同步）
DEFAULT_THRESHOLDS: dict[str, float] = {
    "low":      3.5,
    "normal":   4.0,
    "elevated": 5.0,
    "high":     6.0,
}

# 各 risk_temperature 的允許範圍（不得超出）
THRESHOLD_BOUNDS: dict[str, tuple[float, float]] = {
    "low":      (2.5, 4.5),
    "normal":   (3.0, 5.5),
    "elevated": (3.5, 6.5),
    "high":     (4.5, 7.5),
}

# 最大單次調整幅度
MAX_STEP = 0.5

# 自動套用所需最低樣本數
MIN_SAMPLES = 10

# win_rate 門檻
WIN_RATE_HIGH = 0.60   # 高於此 → 放寬 (門檻 -0.5)
WIN_RATE_LOW  = 0.40   # 低於此 → 收緊 (門檻 +0.5)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_calibration(
    chain_breakdown: dict,
    current_thresholds: dict[str, float],
) -> dict:
    """
    計算建議門檻與是否自動套用。

    Returns:
        {
            "suggestions": {risk_level: {"current": float, "suggested": float, "delta": float, "reason": str}},
            "auto_apply": bool,
            "auto_apply_reason": str,
            "new_thresholds": dict,  # 若 auto_apply=True 則已套用，否則與 current 相同
        }
    """
    rule = chain_breakdown.get("rule_engine", {})
    rule_total = rule.get("total", 0)
    rule_win_rate = rule.get("win_rate")  # None or float 0.0–1.0

    suggestions: dict[str, dict] = {}
    auto_apply = False
    auto_apply_reason = "樣本不足或勝率在正常區間，不自動套用"

    # 只有 rule_engine 有足夠樣本且 win_rate 已計算時才觸發
    if rule_win_rate is not None and rule_total >= MIN_SAMPLES:
        if rule_win_rate < WIN_RATE_LOW:
            direction = +MAX_STEP
            reason_tmpl = f"rule_engine 勝率 {rule_win_rate:.1%} < {WIN_RATE_LOW:.0%}，收緊門檻 +{MAX_STEP}"
            auto_apply = True
            auto_apply_reason = reason_tmpl
        elif rule_win_rate >= WIN_RATE_HIGH:
            direction = -MAX_STEP
            reason_tmpl = f"rule_engine 勝率 {rule_win_rate:.1%} ≥ {WIN_RATE_HIGH:.0%}，放寬門檻 -{MAX_STEP}"
            auto_apply = True
            auto_apply_reason = reason_tmpl
        else:
            direction = 0.0
            reason_tmpl = f"rule_engine 勝率 {rule_win_rate:.1%} 在正常區間，不調整"
    else:
        direction = 0.0
        if rule_win_rate is None:
            reason_tmpl = "rule_engine win_rate 尚未計算（等待更多 T+N 回填）"
        else:
            reason_tmpl = f"rule_engine 樣本數 {rule_total} < {MIN_SAMPLES}，不足以觸發自動校正"

    new_thresholds = dict(current_thresholds)
    for risk_level, current_val in current_thresholds.items():
        lo, hi = THRESHOLD_BOUNDS[risk_level]
        suggested = _clamp(current_val + direction, lo, hi)
        actual_delta = round(suggested - current_val, 4)
        suggestions[risk_level] = {
            "current": current_val,
            "suggested": suggested,
            "delta": actual_delta,
            "reason": reason_tmpl if actual_delta != 0 else f"無調整 — {reason_tmpl}",
        }
        if auto_apply:
            new_thresholds[risk_level] = suggested

    return {
        "suggestions": suggestions,
        "auto_apply": auto_apply,
        "auto_apply_reason": auto_apply_reason,
        "new_thresholds": new_thresholds,
        "rule_engine_samples": rule_total,
        "rule_engine_win_rate": rule_win_rate,
    }


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def load_current_thresholds(state_dir: Path) -> dict[str, float]:
    """讀取已套用的門檻，不存在時回傳預設值。"""
    path = state_dir / "calibrated_thresholds.json"
    saved = safe_load_json(path, {})
    result = dict(DEFAULT_THRESHOLDS)
    for k in result:
        if k in saved and isinstance(saved[k], (int, float)):
            result[k] = float(saved[k])
    return result


def save_suggestion(state_dir: Path, result: dict, dry_run: bool) -> None:
    payload = {
        "generated_at": datetime.now(tz=TW_TZ).isoformat(),
        "dry_run": dry_run,
        "auto_apply": result["auto_apply"],
        "auto_apply_reason": result["auto_apply_reason"],
        "rule_engine_samples": result["rule_engine_samples"],
        "rule_engine_win_rate": result["rule_engine_win_rate"],
        "suggestions": result["suggestions"],
        "new_thresholds": result["new_thresholds"],
    }
    atomic_save_json(state_dir / "calibration_suggestion.json", payload)


def save_applied_thresholds(state_dir: Path, thresholds: dict[str, float]) -> None:
    atomic_save_json(state_dir / "calibrated_thresholds.json", thresholds)


def append_audit(state_dir: Path, result: dict, dry_run: bool, applied: bool) -> None:
    record = {
        "ts": datetime.now(tz=TW_TZ).isoformat(),
        "dry_run": dry_run,
        "auto_apply": result["auto_apply"],
        "applied": applied,
        "auto_apply_reason": result["auto_apply_reason"],
        "rule_engine_samples": result["rule_engine_samples"],
        "rule_engine_win_rate": result["rule_engine_win_rate"],
        "new_thresholds": result["new_thresholds"],
    }
    safe_append_jsonl(state_dir / "calibration_audit.jsonl", record)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> dict:
    state_dir = context.get_state_dir()
    quality_report = safe_load_json(state_dir / "decision_quality_report.json", {})
    chain_breakdown = quality_report.get("chain_breakdown", {})
    current_thresholds = load_current_thresholds(state_dir)

    result = compute_calibration(chain_breakdown, current_thresholds)

    # 寫入建議檔（永遠寫）
    save_suggestion(state_dir, result, dry_run)

    # 自動套用：僅在非 dry_run 且觸發條件成立時執行
    applied = False
    if result["auto_apply"] and not dry_run:
        save_applied_thresholds(state_dir, result["new_thresholds"])
        applied = True

    # Audit trail（永遠記錄）
    append_audit(state_dir, result, dry_run, applied)

    status = "已套用" if applied else ("建議已寫入（dry-run）" if dry_run else "建議已寫入（未觸發自動套用）")
    print(f"[calibrate] {status} — rule_engine 樣本={result['rule_engine_samples']}, "
          f"勝率={result['rule_engine_win_rate']}")
    for level, s in result["suggestions"].items():
        if s["delta"] != 0:
            print(f"  {level}: {s['current']} → {s['suggested']} ({s['delta']:+.1f})")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="校正 BUY_THRESHOLD_BY_RISK")
    parser.add_argument("--dry-run", action="store_true", help="只寫建議，不套用")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
