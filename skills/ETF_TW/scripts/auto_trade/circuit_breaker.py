#!/usr/bin/env python3
"""
circuit_breaker.py — 自動交易熔斷器

5 個自動熔斷條件（任一觸發 → 暫停買入掃描）：

  1. 全市場 risk-off：market_event_context.event_regime == 'risk-off'
                    或 global_risk_level in ('high', 'critical')
  2. 重大事件觸發：major_event_flag.triggered == True
  3. 週累計虧損 > 5%（依 daily_pnl 累計）
  4. 連續 5 個交易日有買入觸發 → 強制 1 日冷卻
  5. 任一 critical sensor 失效（sensor_health.healthy == False）
  6. 當日下單金額累計 > 可交割金額 × 50%
  7. master switch 關閉（auto_trade_config.enabled == False）

state 檔案：
  auto_trade_circuit_breaker.json   當前熔斷器狀態
  auto_trade_phase2_config.json     master switch + 自訂閾值（Phase 2 獨立，
                                    避免與舊版 auto_trade_config.json 衝突）

回傳格式：
  {
    "buy_allowed": bool,
    "reasons": [str, ...],         # 若 buy_allowed=False 列出所有觸發原因
    "checks": [{"name", "passed", "detail"}, ...],
  }
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

TW_TZ = ZoneInfo("Asia/Taipei")

# 預設閾值（auto_trade_config.json 可覆蓋）
DEFAULT_WEEKLY_LOSS_LIMIT_PCT = 0.05
DEFAULT_CONSECUTIVE_BUY_DAYS_LIMIT = 5
DEFAULT_DAILY_AUTO_BUY_PCT = 0.50  # 可交割金額 × 50%（D6=B 複用 max_buy_amount_pct）


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CircuitBreakerResult:
    buy_allowed: bool
    reasons: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "buy_allowed": self.buy_allowed,
            "reasons": self.reasons,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
        }


def _safe_load(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def _now() -> datetime:
    return datetime.now(tz=TW_TZ)


def load_auto_trade_config(state_dir: Path) -> dict:
    """
    讀取 Phase 2 自動交易設定（含 master switch）。

    使用獨立檔名 `auto_trade_phase2_config.json`，避免與舊版
    `auto_trade_config.json` 衝突（後者由舊的 auto_decision_scan 使用）。

    若 phase2 設定檔不存在則回傳預設值（enabled=False，需要使用者主動啟用）。
    """
    cfg_path = state_dir / "auto_trade_phase2_config.json"
    cfg = _safe_load(cfg_path, default={})
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "weekly_loss_limit_pct": float(cfg.get("weekly_loss_limit_pct", DEFAULT_WEEKLY_LOSS_LIMIT_PCT)),
        "consecutive_buy_days_limit": int(cfg.get("consecutive_buy_days_limit", DEFAULT_CONSECUTIVE_BUY_DAYS_LIMIT)),
        "daily_auto_buy_pct": float(cfg.get("daily_auto_buy_pct", DEFAULT_DAILY_AUTO_BUY_PCT)),
    }


def save_circuit_breaker_state(state_dir: Path, result: CircuitBreakerResult) -> None:
    path = state_dir / "auto_trade_circuit_breaker.json"
    payload = {
        **result.as_dict(),
        "checked_at": _now().isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_master_switch(config: dict) -> CheckResult:
    enabled = bool(config.get("enabled", False))
    return CheckResult(
        name="master_switch",
        passed=enabled,
        detail="auto_trade.enabled=True" if enabled else "auto_trade.enabled=False（master switch off）",
    )


def check_market_risk(state_dir: Path) -> CheckResult:
    mec = _safe_load(state_dir / "market_event_context.json", default={})
    regime = mec.get("event_regime", "")
    risk_level = mec.get("global_risk_level", "")
    if regime == "risk-off":
        return CheckResult(name="market_risk", passed=False, detail=f"event_regime=risk-off")
    if risk_level in ("high", "critical"):
        return CheckResult(name="market_risk", passed=False, detail=f"global_risk_level={risk_level}")
    return CheckResult(name="market_risk", passed=True, detail=f"regime={regime} level={risk_level or 'low'}")


def check_major_event(state_dir: Path) -> CheckResult:
    mef = _safe_load(state_dir / "major_event_flag.json", default={})
    if mef.get("triggered"):
        level = mef.get("level", "unknown")
        reason = mef.get("reason", "")[:60]
        return CheckResult(name="major_event", passed=False, detail=f"[{level}] {reason}")
    return CheckResult(name="major_event", passed=True, detail="未觸發")


def check_sensor_health(state_dir: Path) -> CheckResult:
    sh = _safe_load(state_dir / "sensor_health.json", default={})
    if not sh:
        # 沒有 sensor_health.json 視為通過（避免初次部署誤擋）
        return CheckResult(name="sensor_health", passed=True, detail="尚無 sensor_health.json")
    healthy = bool(sh.get("healthy", True))
    failures = sh.get("critical_failures", [])
    if healthy:
        return CheckResult(name="sensor_health", passed=True, detail="所有關鍵感測器正常")
    return CheckResult(
        name="sensor_health",
        passed=False,
        detail=f"關鍵失效: {', '.join(failures) if failures else 'unknown'}",
    )


def check_weekly_loss(state_dir: Path, limit_pct: float) -> CheckResult:
    """
    讀取 daily_pnl.json 的近 7 日累計損益，與 limit_pct 比較。
    若 daily_pnl 沒有 cumulative 數據則視為通過（保守）。
    """
    pnl = _safe_load(state_dir / "daily_pnl.json", default={})
    # daily_pnl 可能有 weekly_pnl_pct 或需要從 history 算
    weekly_pct = pnl.get("weekly_pnl_pct")
    if weekly_pct is None:
        return CheckResult(name="weekly_loss", passed=True, detail="無週累計損益資料，預設通過")
    if weekly_pct < -limit_pct:
        return CheckResult(
            name="weekly_loss",
            passed=False,
            detail=f"週累計虧損 {weekly_pct:.2%} > 上限 {limit_pct:.0%}",
        )
    return CheckResult(name="weekly_loss", passed=True, detail=f"週累計 {weekly_pct:+.2%}")


def check_consecutive_buy_days(history_path: Path, limit_days: int) -> CheckResult:
    """
    檢查最近 N 個交易日是否每日都有 executed 的 buy 訊號。
    若連續達到 limit_days 則強制冷卻 1 日（今日不准）。
    """
    if not history_path.exists():
        return CheckResult(name="consecutive_buy_days", passed=True, detail="history 不存在")

    today = _now().date()
    # 取最近 limit_days 個日期
    target_dates = [(today - timedelta(days=i)).isoformat() for i in range(1, limit_days + 1)]
    days_with_buy: set[str] = set()

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("side") != "buy":
                    continue
                if rec.get("_event") != "status_changed_to_executed":
                    continue
                date_part = (rec.get("created_at") or "")[:10]
                if date_part in target_dates:
                    days_with_buy.add(date_part)
    except OSError:
        return CheckResult(name="consecutive_buy_days", passed=True, detail="history 讀取失敗")

    if len(days_with_buy) >= limit_days:
        return CheckResult(
            name="consecutive_buy_days",
            passed=False,
            detail=f"前 {limit_days} 個日期全部有買入，今日強制冷卻",
        )
    return CheckResult(
        name="consecutive_buy_days",
        passed=True,
        detail=f"前 {limit_days} 日中 {len(days_with_buy)} 日有買入",
    )


def check_daily_buy_amount(
    queue_path: Path,
    settlement_safe_cash: float,
    daily_pct: float,
) -> CheckResult:
    """
    檢查當日（pending + acked + executed）買入金額累計 vs 可交割金額 × pct。
    """
    from .pending_queue import sum_today_buy_amount
    if settlement_safe_cash <= 0:
        return CheckResult(
            name="daily_buy_amount",
            passed=False,
            detail=f"settlement_safe_cash={settlement_safe_cash} ≤ 0，無可用額度",
        )
    used = sum_today_buy_amount(queue_path)
    limit = settlement_safe_cash * daily_pct
    if used > limit:
        return CheckResult(
            name="daily_buy_amount",
            passed=False,
            detail=f"當日累計 {used:.0f} > 上限 {limit:.0f}（可交割 {settlement_safe_cash:.0f} × {daily_pct:.0%}）",
        )
    return CheckResult(
        name="daily_buy_amount",
        passed=True,
        detail=f"當日累計 {used:.0f} / {limit:.0f}",
    )


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def evaluate_buy_allowed(
    state_dir: Path,
    *,
    settlement_safe_cash: float,
    queue_path: Path | None = None,
    history_path: Path | None = None,
) -> CircuitBreakerResult:
    """
    跑完所有買入熔斷檢查。

    Args:
        state_dir: state 目錄
        settlement_safe_cash: 可交割金額（從 account_snapshot 來）
        queue_path: pending_auto_orders.json 路徑（不給就略過 daily_buy_amount 檢查）
        history_path: auto_trade_history.jsonl 路徑（不給就略過 consecutive 檢查）
    """
    config = load_auto_trade_config(state_dir)
    queue_path = queue_path or (state_dir / "pending_auto_orders.json")
    history_path = history_path or (state_dir / "auto_trade_history.jsonl")

    checks = [
        check_master_switch(config),
        check_market_risk(state_dir),
        check_major_event(state_dir),
        check_sensor_health(state_dir),
        check_weekly_loss(state_dir, config["weekly_loss_limit_pct"]),
        check_consecutive_buy_days(history_path, config["consecutive_buy_days_limit"]),
        check_daily_buy_amount(queue_path, settlement_safe_cash, config["daily_auto_buy_pct"]),
    ]

    failures = [c for c in checks if not c.passed]
    result = CircuitBreakerResult(
        buy_allowed=len(failures) == 0,
        reasons=[f"{c.name}: {c.detail}" for c in failures],
        checks=checks,
    )
    return result
