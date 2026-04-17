#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import subprocess
import sys
# Force default agent before importing ETF core
import os
if not os.environ.get('AGENT_ID') and not os.environ.get('OPENCLAW_AGENT_NAME'):
    os.environ['AGENT_ID'] = 'etf_master'
    os.environ['ETF_TW_AGENT_ID_FORCED'] = 'true'

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.append(str(ROOT))
sys.path.append(str(SCRIPTS_DIR))
from scripts.etf_core import context
import scripts.pre_flight_gate as pre_flight
from state_reconciliation import reconciliation_summary
from dashboard_health import build_health_summary_payload
from filled_reconciliation import load_reconciliation_report, build_reconciliation_warnings
from market_calendar_tw import get_today_market_status
from ai_review_lifecycle import update_review_status
from ai_outcome_lifecycle import record_outcome
from ai_auto_reflection import auto_reflect_if_ready
from auto_quality_refresh import auto_refresh_quality_state
from provenance_logger import provenance_summary as get_provenance_summary

# Multi-tenant Context
STATE = context.get_state_dir()
CONFIG_PATH = context.get_instance_config()
FILLED_RECONCILIATION_PATH = STATE / "filled_reconciliation.json"

ETF_DATA_PATH = ROOT / "data" / "etfs.json"
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
app = FastAPI(title="ETF_TW Dashboard")
PYTHON_VENV = ROOT / ".venv" / "bin" / "python3"
if not PYTHON_VENV.exists():
    PYTHON_VENV = ROOT / ".venv" / "bin" / "python"
if not PYTHON_VENV.exists():
    PYTHON_VENV = Path(sys.executable)

ALLOWED_BASE_STRATEGIES = ["平衡配置", "核心累積", "收益優先", "防守保守", "觀察模式"]
ALLOWED_SCENARIO_OVERLAYS = ["無", "逢低觀察", "高波動警戒", "減碼保守", "收益再投資"]

# Per-Agent Strategy Link
instance_id = context.get_instance_id()
INSTANCE_DIR = context.get_instance_dir()
ETF_MASTER_STRATEGY_PATH = INSTANCE_DIR / "strategy_state.json"
STATE_STRATEGY_LINK_PATH = STATE / "strategy_link.json"


class StrategyUpdateRequest(BaseModel):
    base_strategy: str
    scenario_overlay: str


class AutoTradeConfigRequest(BaseModel):
    enabled: bool
    frequency_minutes: int


class AutoTradeSubmitRequest(BaseModel):
    """Submit the current preview candidate as a real order.
    Requires explicit confirmation text to prevent accidental submissions."""
    symbol: str
    action: Literal["buy", "sell"]
    quantity: int
    price: float | None = None  # None = market order
    mode: Literal["paper", "live"] = "paper"
    confirmation: str  # Must match "CONFIRM {symbol} {action} {quantity}" exactly


class TradingModeRequest(BaseModel):
    mode: Literal["live", "paper"]


class TradeRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    price: float


class AIDecisionReviewRequest(BaseModel):
    status: Literal["reviewed", "superseded"]
    human_feedback: str | None = None


class AIDecisionOutcomeRequest(BaseModel):
    outcome_status: Literal["tracked", "reviewed"]
    outcome_note: str
    human_feedback: str | None = None


class SafetyRedlinesRequest(BaseModel):
    max_buy_amount_twd: float
    max_buy_amount_pct: float
    max_buy_shares: int
    max_concentration_pct: float
    daily_loss_limit_pct: float
    ai_confidence_threshold: float
    enabled: bool


class LiveUnlockRequest(BaseModel):
    confirm_1: str
    confirm_2: str


TradingModeRequest.model_rebuild()
AIDecisionReviewRequest.model_rebuild()
AIDecisionOutcomeRequest.model_rebuild()


def load_etf_catalog() -> dict:
    if not ETF_DATA_PATH.exists():
        return {}
    payload = json.loads(ETF_DATA_PATH.read_text(encoding="utf-8"))
    return payload.get("etfs", {})


def normalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper()
    for suffix in (".TW", ".TWO"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def infer_watchlist_group(etf_info: dict) -> str:
    category = (etf_info.get("category") or "").strip()
    if category == "大盤型":
        return "core"
    if category == "高股息":
        return "income"
    if category == "債券型":
        return "defensive"
    return "other"


def build_watchlist_item(symbol: str, etf_info: dict) -> dict:
    group = infer_watchlist_group(etf_info)
    return {
        "symbol": symbol,
        "name": etf_info.get("name", symbol),
        "reason": f"手動加入觀察：{etf_info.get('description', etf_info.get('category', 'ETF 追蹤'))}",
        "category": group,
        "status": "watch",
        "group": group,
    }


def read_watchlist_state() -> dict:
    path = STATE / "watchlist.json"
    if not path.exists():
        return {"items": [], "source": "manual"}
    return json.loads(path.read_text(encoding="utf-8"))


def write_watchlist_state(payload: dict) -> None:
    path = STATE / "watchlist.json"
    payload["updated_at"] = datetime.now().astimezone().isoformat()
    payload.setdefault("source", "manual")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


import os

def refresh_monitoring_state() -> dict:
    script = ROOT / "scripts" / "refresh_monitoring_state.py"
    try:
        env = os.environ.copy()
        result = subprocess.run(
            [str(PYTHON_VENV), str(script)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        refresh_result = {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
        }
        if refresh_result["ok"]:
            try:
                hook = ROOT / "scripts" / "refresh_filled_reconciliation_report.py"
                subprocess.run(
                    [str(PYTHON_VENV), str(hook)],
                    cwd=str(ROOT),
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except Exception:
                pass
        return refresh_result
    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def read_auto_trade_config() -> dict:
    path = STATE / "auto_trade_config.json"
    if not path.exists():
        return {
            "enabled": False,
            "frequency_minutes": 30,
            "trading_hours_only": True,
            "updated_at": None,
            "source": "default",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_auto_trade_config(payload: dict) -> dict:
    path = STATE / "auto_trade_config.json"
    payload["updated_at"] = datetime.now().astimezone().isoformat()
    payload["source"] = "dashboard"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def add_watchlist_symbol(symbol: str) -> dict:
    symbol = normalize_symbol(symbol)
    if not symbol:
        raise ValueError("請輸入 ETF 代號")
    catalog = load_etf_catalog()
    if symbol not in catalog:
        raise ValueError(f"找不到 ETF 代號：{symbol}")
    payload = read_watchlist_state()
    items = payload.get("items", [])
    if any(normalize_symbol(item.get("symbol")) == symbol for item in items):
        raise ValueError(f"{symbol} 已在關注清單中")
    items.append(build_watchlist_item(symbol, catalog[symbol]))
    payload["items"] = items
    write_watchlist_state(payload)
    refresh_result = refresh_monitoring_state()
    return {"ok": True, "symbol": symbol, "refresh": refresh_result}


@app.get("/api/safety-redlines")
async def get_safety_redlines_api():
    path = STATE / "safety_redlines.json"
    if not path.exists():
        from scripts.sync_daily_pnl import DEFAULT_REDLINES
        return DEFAULT_REDLINES
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/safety-redlines/update")
async def update_safety_redlines_api(payload: SafetyRedlinesRequest):
    try:
        path = STATE / "safety_redlines.json"
        data = payload.dict()
        # Mapping confidence threshold to label for UI
        if data['ai_confidence_threshold'] >= 0.85: data['ai_confidence_level'] = "High"
        elif data['ai_confidence_threshold'] >= 0.65: data['ai_confidence_level'] = "Medium"
        else: data['ai_confidence_level'] = "Low"
        
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "redlines": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence")
async def get_intelligence():
    path = STATE / "market_intelligence.json"
    if not path.exists():
        return {"intelligence": {}}
    # 2026.3.31 Hardening: Replace invalid NaN with null before parsing
    try:
        raw_text = path.read_text(encoding="utf-8").replace("NaN", "null")
        return json.loads(raw_text)
    except Exception as e:
        return {"intelligence": {}, "_error": str(e)}


@app.get("/api/decision/consensus")
async def get_decision_consensus():
    path = STATE / "decision_consensus.json"
    if not path.exists():
        return {"consensus": "正在對齊中", "hint": "請點擊「立即規則掃描」以生成最新共識。", "color": "var(--muted)"}
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/history/{symbol}")
async def get_history(symbol: str, period: str = "d"):
    path = STATE / "market_intelligence.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Intelligence data not found")
    
    try:
        raw_text = path.read_text(encoding="utf-8").replace("NaN", "null")
        data = json.loads(raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON Parse Error: {e}")
        
    intel = data.get("intelligence", {}).get(symbol)
    if not intel:
        raise HTTPException(status_code=404, detail=f"History for {symbol} not ready")
    
    # 週期參數處理 (對應 10-02-PLAN)
    raw_history = intel.get("history_30d", [])
    if period == "w":
         raw_history = intel.get("history_weekly", []) or raw_history
    elif period == "m":
         raw_history = intel.get("history_monthly", []) or raw_history

    history = [p for p in raw_history if p.get("c") is not None and p.get("o") is not None]
    indicators = {k: intel[k] for k in ("sma5", "sma20", "sma60", "rsi", "macd", "macd_signal") if k in intel}
    
    return {"symbol": symbol, "history": history, "indicators": indicators}


def remove_watchlist_symbol(symbol: str) -> dict:
    symbol = normalize_symbol(symbol)
    payload = read_watchlist_state()
    items = payload.get("items", [])
    kept = [item for item in items if normalize_symbol(item.get("symbol")) != symbol]
    if len(kept) == len(items):
        raise ValueError(f"{symbol} 不在關注清單中")
    payload["items"] = kept
    write_watchlist_state(payload)
    refresh_result = refresh_monitoring_state()
    return {"ok": True, "symbol": symbol, "refresh": refresh_result}


def write_strategy_state(base_strategy: str, scenario_overlay: str) -> dict:
    if base_strategy not in ALLOWED_BASE_STRATEGIES:
        raise ValueError("invalid base_strategy")
    if scenario_overlay not in ALLOWED_SCENARIO_OVERLAYS:
        raise ValueError("invalid scenario_overlay")

    if ETF_MASTER_STRATEGY_PATH.exists():
        payload = json.loads(ETF_MASTER_STRATEGY_PATH.read_text(encoding="utf-8"))
    else:
        payload = {
            "base_strategy": base_strategy,
            "scenario_overlay": scenario_overlay,
            "source": "dashboard",
            "header_format": None,
        }
    payload["base_strategy"] = base_strategy
    payload["scenario_overlay"] = scenario_overlay
    payload["updated_at"] = datetime.now().astimezone().isoformat()
    ETF_MASTER_STRATEGY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    link_payload = {
        "base_strategy": base_strategy,
        "scenario_overlay": scenario_overlay,
        "updated_at": payload["updated_at"],
        "source": "etf_master",
        "header_format": payload.get("header_format"),
    }
    STATE_STRATEGY_LINK_PATH.write_text(json.dumps(link_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def notify_etf_master_strategy_changed(base_strategy: str, scenario_overlay: str) -> dict:
    import subprocess
    import sys

    script = ROOT / "scripts" / "notify_agent_strategy_change.py"
    result = subprocess.run(
        [sys.executable, str(script), base_strategy, scenario_overlay],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    return {
        "notified": True,
        "delivery": {"status": "runtime-message-required", "sessionKey": payload.get("sessionKey")},
        "message": payload.get("message"),
    }


def notify_etf_master_mode_changed(mode_label: str) -> dict:
    import subprocess
    import sys

    script = ROOT / "scripts" / "notify_agent_mode_change.py"
    result = subprocess.run(
        [sys.executable, str(script), mode_label],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    return {
        "notified": True,
        "delivery": {"status": "runtime-message-required", "sessionKey": payload.get("sessionKey")},
        "message": payload.get("message"),
    }



def load_state(name: str) -> dict:
    path = STATE / name
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else {}
    except Exception:
        return {"_load_warning": f"failed_to_load:{name}"}




def load_etf_name_map() -> dict:
    if not ETF_DATA_PATH.exists():
        return {}
    payload = json.loads(ETF_DATA_PATH.read_text(encoding="utf-8"))
    etfs = payload.get("etfs", {})
    return {symbol: info.get("name", symbol) for symbol, info in etfs.items()}


def classify_position_record(record: dict) -> dict:
    quantity = float(record.get("quantity") or 0)
    source = record.get("source")
    has_cost_or_pnl = any(record.get(k) not in (None, 0, 0.0, "") for k in ["average_cost", "average_price", "unrealized_pnl", "market_value"])
    needs_review = source == "live_broker" and quantity == 0 and has_cost_or_pnl
    return {
        **record,
        "is_residual": False,
        "needs_review": needs_review,
        "holding_status": "券商回傳紀錄" if needs_review else "有效持倉",
    }


def build_trading_mode_summary(trading_mode: dict) -> dict:
    return {
        "mode_label": str(trading_mode.get("effective_mode") or "unknown").upper(),
        "default_account": trading_mode.get("default_account") or "N/A",
        "default_broker": trading_mode.get("default_broker") or "N/A",
        "data_source": trading_mode.get("data_source") or "N/A",
        "health_check": "OK" if trading_mode.get("health_check_ok") else "FAIL",
        "updated_at": trading_mode.get("updated_at") or "N/A",
    }


def resolve_market_session_open(auto_trade_state: dict, market_calendar_status: dict) -> dict:
    source = market_calendar_status.get("source") or "auto_trade_state"
    is_open = bool(market_calendar_status.get("is_open"))
    if source == "market_calendar_tw":
        return {
            "market_session_open": is_open,
            "market_session_label": "交易時段中" if is_open else "休市中",
            "source": source,
            "session": market_calendar_status.get("session"),
        }
    fallback_open = bool(auto_trade_state.get("market_session_open")) if auto_trade_state else is_open
    return {
        "market_session_open": fallback_open,
        "market_session_label": "交易時段中" if fallback_open else "休市中",
        "source": source,
        "session": market_calendar_status.get("session"),
    }


def build_trading_mode_warnings(trading_mode: dict, positions_payload: dict, position_rows: list[dict]) -> list[str]:
    warnings = []
    mode = trading_mode.get("effective_mode")
    source = positions_payload.get("source")
    if mode == "live-ready" and source == "paper_ledger":
        warnings.append("目前模式為 LIVE-READY，但持倉資料仍來自 paper_ledger")
    if mode == "paper" and source == "live_broker":
        warnings.append("目前模式為 PAPER，但持倉資料來自 live_broker")
    broker_record_count = sum(1 for row in position_rows if row.get("needs_review"))
    if broker_record_count:
        warnings.append(f"偵測到 {broker_record_count} 筆券商回傳紀錄（待核對），請勿僅憑 quantity=0 直接判定無持倉")
    return warnings


def build_position_view(positions_payload: dict, market_cache_payload: dict, snapshot_holdings: list[dict] | None = None, watchlist_items: list[dict] | None = None) -> list[dict]:
    quotes = market_cache_payload.get("quotes", {})
    snapshot_map = {item.get("symbol"): item for item in (snapshot_holdings or [])}
    watchlist_map = {item.get("symbol"): item for item in (watchlist_items or [])}
    etf_name_map = load_etf_name_map()
    rows = []
    for p in positions_payload.get("positions", []):
        symbol = p.get("symbol")
        quantity = float(p.get("quantity") or 0)
        avg_cost = float(p.get("average_cost") or p.get("average_price") or 0)
        total_cost = float(p.get("total_cost") or (avg_cost * quantity if quantity > 0 else 0))
        cache_price = float(quotes.get(symbol, {}).get("current_price") or 0)
        snapshot_price = float((snapshot_map.get(symbol) or {}).get("current_price") or 0)
        state_price = float(p.get("current_price") or 0)
        current_price = cache_price or snapshot_price or state_price
        market_value = round(quantity * current_price, 2) if quantity > 0 and current_price else float(p.get("market_value") or total_cost)
        unrealized_pnl = float(p.get("unrealized_pnl") if p.get("unrealized_pnl") is not None else round(market_value - total_cost, 2))
        return_pct = round((unrealized_pnl / total_cost) * 100, 2) if total_cost else 0.0
        name = (snapshot_map.get(symbol) or {}).get("name") or (watchlist_map.get(symbol) or {}).get("name") or etf_name_map.get(symbol, symbol)
        price_source = "market_cache" if cache_price else ("portfolio_snapshot" if snapshot_price else "fallback_cost")
        row = {
            "symbol": symbol,
            "name": name,
            "quantity": quantity,
            "average_cost": avg_cost,
            "total_cost": total_cost,
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "return_pct": return_pct,
            "source": p.get("source"),
            "price_source": price_source,
        }
        rows.append(classify_position_record(row))
    return rows




def classify_freshness(iso_ts: str | None) -> dict:
    if not iso_ts:
        return {"label": "unknown", "level": "warn"}
    try:
        dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        age = (now - dt).total_seconds()
        if age <= 600:
            return {"label": "fresh", "level": "good"}
        if age <= 3600:
            return {"label": "stale", "level": "warn"}
        return {"label": "old", "level": "bad"}
    except Exception:
        return {"label": "invalid", "level": "bad"}


def build_risk_signals(position_rows: list[dict], market_cache: dict, orders_open: dict) -> list[dict]:
    signals = []
    freshness = classify_freshness(market_cache.get("updated_at"))
    signals.append({
        "title": "價格快取新鮮度",
        "detail": freshness["label"],
        "level": freshness["level"],
    })

    zero_price_count = sum(1 for row in position_rows if float(row.get("current_price") or 0) <= 0)
    if zero_price_count:
        signals.append({
            "title": "價格缺失",
            "detail": f"{zero_price_count} 檔持倉缺少有效價格",
            "level": "warn",
        })
    else:
        signals.append({
            "title": "價格覆蓋",
            "detail": "持倉已有價格快取",
            "level": "good",
        })

    open_orders = len(orders_open.get("orders", []))
    signals.append({
        "title": "未完成委託",
        "detail": f"{open_orders} 筆",
        "level": "warn" if open_orders else "good",
    })

    total_market_value = sum(float(r.get("market_value") or 0) for r in position_rows)
    max_row = None
    if total_market_value > 0 and position_rows:
        max_row = max(position_rows, key=lambda r: float(r.get("market_value") or 0))
        weight = (float(max_row.get("market_value") or 0) / total_market_value) * 100
        signals.append({
            "title": "最大持倉集中度",
            "detail": f"{max_row.get('symbol')} / {weight:.2f}%",
            "level": "warn" if weight >= 60 else "good",
        })

    return signals


def build_watchlist_groups(watchlist_rows: list[dict]) -> dict:
    groups = {"core": [], "income": [], "defensive": [], "other": []}
    for item in watchlist_rows:
        group = item.get("group") or "other"
        groups.setdefault(group, []).append(item)
    return groups


def display_watchlist_status(status: str) -> str:
    mapping = {
        "watch": "觀察中",
        "holding-watch": "已持有・觀察中",
    }
    return mapping.get(status, status or "未設定")


def display_watchlist_category(category: str) -> str:
    mapping = {
        "core": "核心",
        "income": "收益",
        "defensive": "防守",
        "other": "其他",
    }
    return mapping.get(category, category or "未分類")


def display_tape_position(pos: str) -> str:
    mapping = {
        "near-low": "低檔區",
        "mid-low": "中低檔",
        "mid": "中性展延",
        "mid-high": "中高檔",
        "near-high": "高檔區",
        "very-high": "極端高標",
        "near-peak": "波段頂部",
        "stable": "橫盤穩健",
        "unknown": "資料缺失",
    }
    return mapping.get(pos, pos or "未定義")


def display_tape_strength(strength: str) -> str:
    mapping = {
        "very-weak": "極端低度",
        "weak": "弱勢壓制",
        "soft": "微幅轉弱",
        "neutral": "勢均力敵",
        "firm": "韌性盤墊",
        "strong": "強勢推升",
        "very-strong": "極端力度",
        "defensive-strong": "防禦性走強",
        "unknown": "觀察中",
    }
    return mapping.get(strength, strength or "未定義")


def display_market_bias(bias: str) -> str:
    mapping = {
        "risk-off": "風險規避 (Risk-Off)",
        "rebound-watch": "反彈觀察",
        "weak": "偏弱震盪",
        "neutral": "多空平衡",
        "bullish": "偏多強勢",
    }
    return mapping.get(bias, bias or "中性")


def build_overview_model() -> dict:
    portfolio_snapshot = load_state("portfolio_snapshot.json")
    account = load_state("account_snapshot.json")
    positions = load_state("positions.json")
    strategy = load_state("strategy_link.json")
    market_cache = load_state("market_cache.json")
    watchlist = load_state("watchlist.json")
    orders_open = load_state("orders_open.json")
    trading_mode = load_state("trading_mode.json")
    auto_trade_config = load_state("auto_trade_config.json")
    auto_trade_state = load_state("auto_trade_state.json")
    auto_trade_config.setdefault("live_submit_allowed", False)
    auto_trade_config.setdefault("preview_only_mode", True)
    auto_trade_state.setdefault("live_submit_allowed", False)
    auto_trade_state.setdefault("preview_only_mode", True)
    auto_preview_candidate = load_state("auto_preview_candidate.json")
    
    # Safety Redlines & PnL
    safety_redlines = load_state("safety_redlines.json")
    if not safety_redlines:
        from scripts.sync_daily_pnl import DEFAULT_REDLINES
        safety_redlines = DEFAULT_REDLINES
    daily_pnl = load_state("daily_pnl.json")

    ai_decision_request = load_state("ai_decision_request.json")
    ai_decision_response = load_state("ai_decision_response.json")
    ai_decision_quality = load_state("ai_decision_quality.json")
    decision_quality = load_state("decision_quality.json")
    major_event_flag = load_state("major_event_flag.json")
    event_review_state = load_state("event_review_state.json")
    market_context_taiwan = load_state("market_context_taiwan.json")
    market_event_context = load_state("market_event_context.json")
    intraday_tape_context = load_state("intraday_tape_context.json")
    market_intelligence = load_state("market_intelligence.json")
    layered_review_status = load_state("layered_review_status.json")
    decision_engine_health = {}
    # Live broker positions should take precedence when available via positions.json.
    # Merge with portfolio_snapshot to ensure complete asset view.
    snapshot_holdings = portfolio_snapshot.get("holdings", [])
    if snapshot_holdings:
        live_symbols = {p.get("symbol") for p in positions.get("positions", [])}
        merged_positions = list(positions.get("positions", []))
        for h in snapshot_holdings:
            if h.get("symbol") not in live_symbols:
                merged_positions.append({
                    "symbol": h.get("symbol"),
                    "quantity": h.get("quantity"),
                    "average_cost": h.get("average_cost"),
                    "total_cost": h.get("total_cost"),
                    "source": portfolio_snapshot.get("source", "portfolio_snapshot"),
                })
        positions["positions"] = merged_positions
        
        account = {
            **account,
            "cash": account.get("cash") if account.get("cash") is not None else portfolio_snapshot.get("cash", 0),
            "trigger_suggestions": portfolio_snapshot.get("trigger_suggestions", []),
        }
        if not account.get("updated_at"):
            account["updated_at"] = portfolio_snapshot.get("updated_at")
    position_rows = build_position_view(positions, market_cache, portfolio_snapshot.get("holdings", []), watchlist.get("items", []))
    trading_mode_summary = build_trading_mode_summary(trading_mode)
    trading_mode_warnings = build_trading_mode_warnings(trading_mode, positions, position_rows)
    market_calendar_payload = load_state("market_calendar_tw.json")
    market_calendar_status = get_today_market_status(datetime.now().astimezone(), market_calendar_payload)
    market_session_status = resolve_market_session_open(auto_trade_state, market_calendar_status)
    if market_calendar_status.get("source") == "market_calendar_tw":
        weekday_guess = datetime.now().astimezone().weekday() < 5 and (900 <= (datetime.now().astimezone().hour * 100 + datetime.now().astimezone().minute) <= 1330)
        if bool(weekday_guess) != bool(market_calendar_status.get("is_open")):
            trading_mode_warnings.append(f"market_calendar: {market_calendar_status.get('session')} 與 weekday 判斷不一致")
    market_value = round(sum(row["market_value"] for row in position_rows), 2)
    total_cost = round(sum(row["total_cost"] for row in position_rows), 2)
    total_unrealized = round(sum(row["unrealized_pnl"] for row in position_rows), 2)
    total_equity = round(float(account.get("cash") or 0) + market_value, 2)
    holdings_map = {h.get("symbol"): h for h in portfolio_snapshot.get("holdings", [])}
    watchlist_rows = []
    for item in watchlist.get("items", []):
        symbol = item.get("symbol")
        quote = market_cache.get("quotes", {}).get(symbol, {})
        holding = holdings_map.get(symbol, {})
        effective_status = item.get("status", "watch")
        if float(holding.get("quantity") or 0) > 0:
            effective_status = "holding-watch"
        watchlist_rows.append({
            **item,
            "status": effective_status,
            "status_label": display_watchlist_status(effective_status),
            "category_label": display_watchlist_category(item.get("category")),
            "holding_quantity": float(holding.get("quantity") or 0),
            "current_price": quote.get("current_price", 0),
            "quote_source": quote.get("source", "N/A"),
            "quote_updated_at": quote.get("updated_at"),
        })
    freshness = classify_freshness(market_cache.get("updated_at"))
    risk_signals = build_risk_signals(position_rows, market_cache, orders_open)
    watchlist_groups = build_watchlist_groups(watchlist_rows)
    reconciliation = reconciliation_summary(positions, portfolio_snapshot, orders_open)

    reconciliation_warnings = []
    if not reconciliation.get("positions_vs_snapshot_match"):
        reconciliation_warnings.append("持倉與資產快照不一致，請檢查同步鏈。")
    if reconciliation.get("open_orders_not_in_positions"):
        reconciliation_warnings.append(f"未成交委託尚未進入持倉：{', '.join(reconciliation.get('open_orders_not_in_positions', []))}")
    lag = reconciliation.get("snapshot_lag_sec")
    if lag is not None and lag > 300:
        reconciliation_warnings.append(f"資產快照延遲 {int(lag)} 秒，建議重新同步。")

    filled_reconciliation = load_reconciliation_report(FILLED_RECONCILIATION_PATH)
    reconciliation_warnings.extend(build_reconciliation_warnings(filled_reconciliation))

    decision_engine_health = build_health_summary_payload(
        market_event_context=market_event_context,
        market_context_taiwan=market_context_taiwan,
        major_event_flag=major_event_flag,
        decision_quality=decision_quality,
        auto_trade_state=auto_trade_state,
        market_intelligence=market_intelligence,
        reconciliation_warnings=reconciliation_warnings,
        classify_freshness=classify_freshness,
    )
    intelligence_warning = None
    for w in decision_engine_health.get("warnings", []):
        if "market_intelligence: 無可用技術指標資料" in w:
            intelligence_warning = w
            break

    # Enhance Tape Context for display
    tape_rows = []
    for s in intraday_tape_context.get('watchlist_signals', []):
        tape_rows.append({
            **s,
            "position_label": display_tape_position(s.get('intraday_position')),
            "strength_label": display_tape_strength(s.get('relative_strength')),
        })
    intraday_tape_context['watchlist_signals_display'] = tape_rows
    intraday_tape_context['market_bias_label'] = display_market_bias(intraday_tape_context.get('market_bias'))

    # AI Bridge display alignment:
    # When no AI response exists yet, do NOT label it as Fresh; show 尚無.
    ai_bridge_has_request = bool(ai_decision_request.get("request_id"))
    ai_bridge_has_response = bool(
        ai_decision_response.get("generated_at")
        or ai_decision_response.get("decision")
        or ai_decision_response.get("candidate")
    )
    # Treat missing 'stale' as unknown; only True means stale.
    ai_bridge_stale = None if not ai_bridge_has_response else (ai_decision_response.get("stale") is True)
    ai_bridge_status_label = "尚無" if not ai_bridge_has_response else ("Stale" if ai_bridge_stale else "Fresh")
    ai_bridge = {
        "available": True,
        "has_request": ai_bridge_has_request,
        "has_response": ai_bridge_has_response,
        "generated_at": ai_decision_response.get("generated_at"),
        "stale": ai_bridge_stale,
        "status_label": ai_bridge_status_label,
    }

    # Provenance summary — recent decision trail
    provenance_path = STATE / "decision_provenance.jsonl"
    prov = get_provenance_summary(provenance_path, limit=10)

    return {
        "account": {
            **account,
            "market_value": market_value,
            "total_equity": total_equity,
            "total_cost": total_cost,
            "total_unrealized_pnl": total_unrealized,
            "trigger_suggestions": portfolio_snapshot.get("trigger_suggestions", []),
            "tracked_count": len(position_rows),
        },
        "positions": positions,
        "position_rows": position_rows,
        "strategy": strategy,
        "trading_mode": trading_mode,
        "trading_mode_summary": trading_mode_summary,
        "trading_mode_warnings": trading_mode_warnings,
        "market_calendar_status": market_calendar_status,
        "market_session_status": market_session_status,
        "market_cache": market_cache,
        "watchlist": watchlist,
        "watchlist_rows": watchlist_rows,
        "watchlist_groups": watchlist_groups,
        "orders_open": orders_open,
        "auto_trade_config": auto_trade_config,
        "auto_trade_state": auto_trade_state,
        "safety_redlines": safety_redlines,
        "daily_pnl": daily_pnl,
        "auto_preview_candidate": auto_preview_candidate,
        "ai_decision_request": ai_decision_request,
        "ai_decision_response": ai_decision_response,
        "ai_decision_quality": ai_decision_quality,
        "ai_bridge": ai_bridge,
        "decision_quality": decision_quality,
        "major_event_flag": major_event_flag,
        "event_review_state": event_review_state,
        "market_context_taiwan": market_context_taiwan,
        "market_event_context": market_event_context,
        "intraday_tape_context": intraday_tape_context,
        "layered_review_status": layered_review_status,
        "decision_engine_health": decision_engine_health,
        "intelligence_warning": intelligence_warning,
        "freshness": freshness,
        "risk_signals": risk_signals,
        "state_reconciliation": reconciliation,
        "state_reconciliation_warnings": reconciliation_warnings,
        "filled_reconciliation": filled_reconciliation,
        "provenance_summary": prov,
    }


@app.get("/health")
def health() -> dict:
    overview = build_overview_model()
    warnings = overview.get("state_reconciliation_warnings", [])
    health_summary = overview.get("decision_engine_health", {}).get("health_summary", "unknown")
    return {
        "ok": health_summary == "正常",
        "health_summary": health_summary,
        "warnings": warnings,
        "state_reconciliation": overview.get("state_reconciliation", {}),
    }


@app.get("/api/overview")
def overview_api() -> dict:
    return build_overview_model()


@app.get("/", response_class=HTMLResponse)
def overview_page(request: Request):
    model = build_overview_model()
    context = {
        "request": request,
        "title": "ETF_TW Dashboard",
        **model,
    }
    return templates.TemplateResponse(request, "overview.html", context)


@app.post("/api/strategy/update")
def strategy_update(payload: StrategyUpdateRequest):
    try:
        updated = write_strategy_state(payload.base_strategy, payload.scenario_overlay)
        notify = notify_etf_master_strategy_changed(payload.base_strategy, payload.scenario_overlay)
        # Task 2: 成功更新後觸發 re-scan 以連動 Dashboard
        rescan = _run_full_pipeline_helper()
        return {
            "ok": True,
            "strategy_state": updated,
            "notify": notify,
            "rescan": rescan,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/trading-mode/set")
def trading_mode_set(payload: TradingModeRequest):
    try:
        script = ROOT / "scripts" / "etf_tw.py"
        subprocess.run([str(PYTHON_VENV), str(script), "mode", payload.mode], cwd=str(ROOT), capture_output=True, text=True, check=True)
        
        # Non-blocking refresh (or at least don't crash if refresh has issues)
        try:
            refresh_monitoring_state()
            refresh_status = "ok"
        except Exception as e:
            refresh_status = f"partial_failure:{str(e)}"
            
        model = build_overview_model()
        summary = model.get("trading_mode_summary", {})
        mode_label = summary.get("mode_label") or payload.mode
        notify = notify_etf_master_mode_changed(mode_label)
        
        return {
            "ok": True,
            "trading_mode": model.get("trading_mode"),
            "trading_mode_summary": summary,
            "warnings": model.get("trading_mode_warnings", []),
            "notify": notify,
            "refresh_status": refresh_status,
        }
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() or e.stdout.strip() or str(e)
        raise HTTPException(status_code=400, detail=detail)


@app.post("/api/watchlist/add")
def watchlist_add(symbol: str = Form(...)):
    try:
        return add_watchlist_symbol(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/watchlist/remove")
def watchlist_remove(symbol: str = Form(...)):
    try:
        return remove_watchlist_symbol(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/refresh")
def refresh_dashboard_state():
    result = refresh_monitoring_state()
    if not result.get("ok"):
        detail = (result.get("stderr") or result.get("stdout") or "未知錯誤").strip()
        raise HTTPException(status_code=500, detail=f"資料更新失敗：{detail}")
    return {
        "ok": True,
        "message": "資料已完成更新",
        "updated_at": datetime.now().astimezone().isoformat(),
    }


@app.post("/api/ai-decision/refresh-background")
def ai_decision_refresh_background():
    result = refresh_monitoring_state()
    if not result.get("ok"):
        detail = (result.get("stderr") or result.get("stdout") or "未知錯誤").strip()
        raise HTTPException(status_code=500, detail=f"背景資訊刷新失敗：{detail}")
    return {
        "ok": True,
        "message": "背景資訊已刷新",
        "updated_at": datetime.now().astimezone().isoformat(),
    }


@app.post("/api/ai-decision/generate")
def ai_decision_generate():
    try:
        quality = auto_refresh_quality_state(STATE)
        request_script = ROOT / "scripts" / "generate_ai_decision_request.py"
        response_script = ROOT / "scripts" / "generate_ai_decision_response.py"
        subprocess.run([str(PYTHON_VENV), str(request_script), str(STATE)], cwd=str(ROOT), capture_output=True, text=True, check=True)
        subprocess.run([str(PYTHON_VENV), str(response_script), str(STATE)], cwd=str(ROOT), capture_output=True, text=True, check=True)
        # Re-evaluate both decision chains after AI Bridge update
        rescan = _run_full_pipeline_helper()
        return {"ok": True, "message": "AI 建議已生成，正在重新檢討兩條決策鏈…", "quality": quality, "rescan": rescan}
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() or e.stdout.strip() or str(e)
        raise HTTPException(status_code=500, detail=detail)


@app.post("/api/ai-decision/rerun")
def ai_decision_rerun():
    try:
        refresh_result = refresh_monitoring_state()
        if not refresh_result.get("ok"):
            detail = (refresh_result.get("stderr") or refresh_result.get("stdout") or "未知錯誤").strip()
            raise HTTPException(status_code=500, detail=f"背景資訊刷新失敗：{detail}")
        quality = auto_refresh_quality_state(STATE)
        request_script = ROOT / "scripts" / "generate_ai_decision_request.py"
        response_script = ROOT / "scripts" / "generate_ai_decision_response.py"
        subprocess.run([str(PYTHON_VENV), str(request_script), str(STATE)], cwd=str(ROOT), capture_output=True, text=True, check=True)
        subprocess.run([str(PYTHON_VENV), str(response_script), str(STATE)], cwd=str(ROOT), capture_output=True, text=True, check=True)
        # Re-evaluate both decision chains after full rerun
        rescan = _run_full_pipeline_helper()
        return {"ok": True, "message": "AI Decision pipeline 已全部重跑，正在重新檢討兩條決策鏈…", "quality": quality, "rescan": rescan}
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() or e.stdout.strip() or str(e)
        raise HTTPException(status_code=500, detail=detail)


@app.post("/api/ai-decision/review")
def ai_decision_review(payload: AIDecisionReviewRequest):
    try:
        updated = update_review_status(STATE, status=payload.status, human_feedback=payload.human_feedback)
        reflection = auto_reflect_if_ready(STATE)
        quality = auto_refresh_quality_state(STATE)
        return {"ok": True, "message": f"AI Decision 已標記為 {payload.status}", "review": updated.get("review", {}), "reflection": reflection, "quality": quality}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai-decision/outcome")
def ai_decision_outcome(payload: AIDecisionOutcomeRequest):
    try:
        row = record_outcome(STATE, outcome_status=payload.outcome_status, outcome_note=payload.outcome_note, human_feedback=payload.human_feedback)
        reflection = auto_reflect_if_ready(STATE)
        quality = auto_refresh_quality_state(STATE)
        return {"ok": True, "message": f"AI Outcome 已記錄為 {payload.outcome_status}", "outcome": row, "reflection": reflection, "quality": quality}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trade/preview")
def trade_preview(payload: TradeRequest):
    overview = build_overview_model()
    account = overview["account"]
    positions = overview["positions"]
    
    # Context for pre_flight_gate
    # Use actual inventory if available
    inventory = {p["symbol"]: p["quantity"] for p in positions.get("positions", [])}
    
    context_data = {
        "cash": account.get("cash", 0.0),
        "inventory": inventory,
        "max_concentration_pct": 0.5,  # Slightly more relaxed for manual
        "max_single_limit_twd": 1000000.0,
        "risk_temperature": 1.0,
        "force_trading_hours": False,  # Manual dashboard allows preview anytime
    }
    
    order = {
        "symbol": payload.symbol,
        "side": payload.side,
        "quantity": payload.quantity,
        "price": payload.price,
        "order_type": "limit",
        "lot_type": "board" if payload.quantity >= 1000 else "odd",
    }
    
    check_res = pre_flight.check_order(order, context_data)
    
    return {
        "ok": True,
        "symbol": payload.symbol,
        "side": payload.side,
        "quantity": payload.quantity,
        "price": payload.price,
        "estimated_total": round(payload.quantity * payload.price, 2),
        "pre_flight": {
            "ok": check_res.get("passed", False),
            "reason": check_res.get("reason", "unknown_error"),
            "details": check_res.get("details", {})
        }
    }


@app.post("/api/trade/submit")
def trade_submit(payload: TradeRequest):
    # Re-run pre_flight_gate check
    overview = build_overview_model()
    account = overview["account"]
    positions = overview["positions"]
    trading_mode = overview["trading_mode"]
    
    inventory = {p["symbol"]: p["quantity"] for p in positions.get("positions", [])}
    mode = str(trading_mode.get("effective_mode") or "paper").lower()
    if mode == "live-ready": mode = "live"
    
    context_data = {
        "cash": account.get("cash", 0.0),
        "inventory": inventory,
        "max_concentration_pct": 0.5,
        "max_single_limit_twd": 1000000.0,
        "risk_temperature": 1.0,
        "force_trading_hours": True, # Force trading hours for actual submission
    }
    
    order = {
        "symbol": payload.symbol,
        "side": payload.side,
        "quantity": payload.quantity,
        "price": payload.price,
        "order_type": "limit",
        "lot_type": "board" if payload.quantity >= 1000 else "odd",
    }
    
    check_res = pre_flight.check_order(order, context_data)
    if not check_res.get("passed"):
        raise HTTPException(status_code=403, detail=f"Risk check failed: {check_res.get('reason')}")
    
    # Build command for complete_trade.py
    cmd_args = [
        str(PYTHON_VENV),
        str(ROOT / "scripts" / "complete_trade.py"),
        payload.symbol,
        payload.side,
        str(payload.quantity),
        "--price", str(payload.price),
        "--mode", mode,
        "--broker", trading_mode.get("default_broker", "sinopac"),
        "--account", trading_mode.get("default_account", "sinopac_01"),
    ]
    
    try:
        result = subprocess.run(cmd_args, cwd=str(ROOT), capture_output=True, text=True, timeout=120, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "未知錯誤").strip()
            raise HTTPException(status_code=500, detail=f"交易執行失敗：{detail}")
            
        return {
            "ok": True,
            "message": f"委託成功送出：{payload.side.upper()} {payload.symbol} {payload.quantity}股 @ {payload.price}",
            "stdout": result.stdout[:500]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auto-trade/config")
def update_auto_trade_config(payload: AutoTradeConfigRequest):
    try:
        if payload.frequency_minutes not in {15, 30, 60}:
            raise ValueError("frequency_minutes 只允許 15 / 30 / 60")
        current = read_auto_trade_config()
        current["enabled"] = payload.enabled
        current["frequency_minutes"] = payload.frequency_minutes
        current["trading_hours_only"] = True
        saved = write_auto_trade_config(current)
        # Re-evaluate both decision chains after config change
        rescan = _run_full_pipeline_helper()
        return {"ok": True, "config": saved, "rescan": rescan}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auto-trade/scan")
def run_auto_trade_scan():
    try:
        script = ROOT / "scripts" / "run_auto_decision_scan.py"
        result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT), capture_output=True, text=True, check=True)
        return {"ok": True, "message": result.stdout.strip() or "AUTO_DECISION_SCAN_OK"}
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() or e.stdout.strip() or str(e)
        raise HTTPException(status_code=500, detail=detail)


def _run_full_pipeline_helper() -> dict:
    """Helper: run rule engine scan and then generate consensus.
    Called after any decision-chain update to re-evaluate both chains together."""
    try:
        # Task 1: 清除舊的仲裁結果，讓 UI 進入 Refresh 狀態
        path = STATE / "decision_consensus.json"
        if path.exists():
            path.unlink()
        
        # 執行掃描後緊接著執行仲裁
        scan_script = ROOT / "scripts" / "run_auto_decision_scan.py"
        consensus_script = ROOT.parent.parent / "scripts" / "generate_decision_consensus.py"
        
        cmd = f"{sys.executable} {scan_script} && {sys.executable} {consensus_script}"
        subprocess.Popen(cmd, shell=True, cwd=str(ROOT))
        
        return {"ok": True, "message": "已啟動背景重新掃描與對齊", "rescan": True, "background": True}
    except Exception as e:
        return {"ok": False, "message": f"共識重檢失敗: {str(e)}", "rescan": False}


PIPELINE_LOCK_PATH = STATE / "full_pipeline.lock"


def _run_full_pipeline_helper() -> dict:
    """依序執行報價同步、規則掃描、仲裁共識的全鏈路管線。"""
    if PIPELINE_LOCK_PATH.exists():
        # 檢查鎖是否過期 (例如超過 10 分鐘)
        mtime = PIPELINE_LOCK_PATH.stat().st_mtime
        if (datetime.now().timestamp() - mtime) < 600:
            return {
                "ok": False,
                "message": "同步管線正在執行中，請稍候再試。",
                "background": True,
            }
        PIPELINE_LOCK_PATH.unlink()

    try:
        # 1. 建立鎖
        PIPELINE_LOCK_PATH.touch()

        # 2. 刪除舊的共識檔案，觸發 UI 載入狀態
        path = STATE / "decision_consensus.json"
        if path.exists():
            path.unlink()

        # 3. 定義腳本路徑
        refresh_script = ROOT / "scripts" / "refresh_monitoring_state.py"
        scan_script = ROOT / "scripts" / "run_auto_decision_scan.py"
        consensus_script = ROOT.parent.parent / "scripts" / "generate_decision_consensus.py"

        # 4. 組合指令串，完成後移除鎖 (不論成功與否都嘗試移除)
        cmd = f"'{sys.executable}' '{refresh_script}' && '{sys.executable}' '{scan_script}' && '{sys.executable}' '{consensus_script}' ; rm -f '{PIPELINE_LOCK_PATH}'"

        # 5. 啟動背景執行
        subprocess.Popen(cmd, shell=True, cwd=str(ROOT))

        return {
            "ok": True,
            "message": "已啟動全流程同步與分析 (Full Sync & Analysis)",
            "background": True,
            "timestamp": datetime.now().astimezone().isoformat(),
        }
    except Exception as e:
        if PIPELINE_LOCK_PATH.exists():
            PIPELINE_LOCK_PATH.unlink()
        return {
            "ok": False,
            "message": f"啟動全鏈路管線失敗: {str(e)}",
            "background": False,
        }


@app.post("/api/decision/full-pipeline")
async def api_full_pipeline():
    """POST 端點觸發全鏈路管線。"""
    result = _run_full_pipeline_helper()
    if not result.get("ok"):
        if "正在執行中" in result.get("message", ""):
            return JSONResponse(status_code=429, content=result)
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@app.post("/api/auto-trade/submit")
async def auto_trade_submit(payload: AutoTradeSubmitRequest):
    """Submit a preview candidate as a real order.
    
    Safety gates:
    1. Confirmation text must exactly match "CONFIRM {symbol} {action} {quantity}"
    2. For live mode, live_submit_allowed must be True in both config and state
    3. Symbol must match the current auto_preview_candidate.json
    4. After submission, verify via list_trades() that the order landed
    """
    import datetime as _dt
    # Gate 1: Confirmation text
    expected = f"CONFIRM {payload.symbol} {payload.action} {payload.quantity}"
    if payload.confirmation != expected:
        raise HTTPException(status_code=400, detail=f"確認文字不符，預期：{expected}")
    
    # Gate 2: Preview candidate must match
    candidate = load_state("auto_preview_candidate.json")
    if not candidate:
        raise HTTPException(status_code=400, detail="目前沒有 preview 候選，無法提交")
    if candidate.get("symbol") != payload.symbol:
        raise HTTPException(status_code=400, detail=f"候選標的不符：preview={candidate.get('symbol')}, 請求={payload.symbol}")
    if candidate.get("not_submitted") is False:
        raise HTTPException(status_code=400, detail="此候選已提交過，不可重複下單")
    
    # Gate 3: Live mode safety
    if payload.mode == "live":
        config = load_state("auto_trade_config.json")
        state = load_state("auto_trade_state.json")
        if not config.get("live_submit_allowed") or not state.get("live_submit_allowed"):
            raise HTTPException(status_code=403, detail="live_submit_allowed 尚未啟用，禁止真實下單")
    
    # Gate 4: Large order check (no CONFIRM LARGE ORDER keyword = block >50% portfolio)
    # (We'll add portfolio percentage check if positions data is available)
    
    # Build command for complete_trade.py
    cmd_args = [
        str(PYTHON_VENV),
        str(ROOT / "scripts" / "complete_trade.py"),
        payload.symbol,
        payload.action,
        str(payload.quantity),
        "--mode", payload.mode,
        "--broker", load_state("trading_mode.json").get("default_broker", "sinopac"),
        "--account", load_state("trading_mode.json").get("default_account", "sinopac_01"),
    ]
    if payload.price:
        cmd_args.extend(["--price", str(payload.price)])
    if candidate.get("reference_price") and not payload.price:
        cmd_args.extend(["--suggested-price", str(candidate["reference_price"])])
    
    try:
        result = subprocess.run(cmd_args, cwd=str(ROOT), capture_output=True, text=True, timeout=120, check=False)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        # Check for broker_order_id in output (教訓10: no broker_order_id = fake receipt)
        has_order_id = "broker_order_id" in stdout or "order_id" in stdout or "委託" in stdout
        
        # Update preview candidate as submitted
        candidate["not_submitted"] = False
        candidate["submitted_at"] = _dt.datetime.now().astimezone().isoformat()
        candidate["submit_mode"] = payload.mode
        candidate["submit_result_stdout"] = stdout[:500]
        candidate["submit_result_stderr"] = stderr[:500] if stderr else ""
        candidate["submit_exit_code"] = result.returncode
        
        path = STATE / "auto_preview_candidate.json"
        path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Append to submission log
        log_path = STATE / "auto_trade_submissions.json"
        log_entries = []
        if log_path.exists():
            try:
                log_entries = json.loads(log_path.read_text(encoding="utf-8"))
            except Exception:
                log_entries = []
        log_entries.append({
            "timestamp": _dt.datetime.now().astimezone().isoformat(),
            "symbol": payload.symbol,
            "action": payload.action,
            "quantity": payload.quantity,
            "price": payload.price,
            "mode": payload.mode,
            "exit_code": result.returncode,
            "has_order_id": has_order_id,
        })
        log_path.write_text(json.dumps(log_entries, ensure_ascii=False, indent=2), encoding="utf-8")
        
        if result.returncode != 0:
            return {
                "ok": False,
                "message": f"complete_trade 執行失敗 (exit={result.returncode})",
                "stdout": stdout[:500],
                "stderr": stderr[:500],
            }
        
        return {
            "ok": True,
            "message": f"委託已送出：{payload.symbol} {payload.action} {payload.quantity} @ {payload.mode}",
            "has_order_id": has_order_id,
            "stdout": stdout[:500],
            "stderr": stderr[:300] if stderr else None,
            "candidate_updated": True,
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="complete_trade 執行逾時（120秒）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失敗：{str(e)[:300]}")


# ---------------------------------------------------------------------------
# Trade Journal API
# ---------------------------------------------------------------------------

@app.get("/api/trade-journal/{target_date}")
def get_trade_journal(target_date: str):
    """Return a specific date's EOD trade journal."""
    from scripts.trade_journal import load_journal
    journal = load_journal(target_date)
    if not journal:
        raise HTTPException(status_code=404, detail=f"No journal found for {target_date}")
    return journal


@app.get("/api/trade-journal")
def list_trade_journals():
    """List all available trade journal dates."""
    from scripts.trade_journal import list_journals
    journals = list_journals()
    return {"dates": journals, "count": len(journals)}


@app.post("/api/trade-journal/generate")
def generate_trade_journal(payload: dict | None = None):
    """Generate (or regenerate) a trade journal for a given date. Defaults to today."""
    from scripts.trade_journal import build_daily_journal, save_journal
    target_date = (payload or {}).get("date")
    journal = build_daily_journal(target_date)
    path = save_journal(journal)
    return {"ok": True, "date": journal["date"], "path": str(path), "summary": journal.get("summary")}


@app.get("/api/decision/quality-report")
async def get_decision_quality_report():
    """決策品質報告 — QUALITY-01"""
    from scripts.etf_core import context as _ctx
    from scripts.etf_core.state_io import safe_load_json
    report_path = _ctx.get_state_dir() / "decision_quality_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="decision_quality_report.json not found. Run generate_decision_quality_report.py first.")
    data = safe_load_json(report_path, default=None)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to load report")
    return data


# ── Live 模式授權閘門 (LIVE-02) ───────────────────────────────────────────────

LIVE_CONFIRM_1 = "ENABLE LIVE TRADING"
LIVE_CONFIRM_2 = "I UNDERSTAND REAL MONEY IS AT RISK"


@app.get("/api/live-mode/status")
async def get_live_mode_status():
    """Live 模式授權狀態 — LIVE-02"""
    from scripts.etf_core import context as _ctx
    from scripts.etf_core.state_io import safe_load_json
    state_dir = _ctx.get_state_dir()
    live_mode = safe_load_json(state_dir / "live_mode.json", default={"enabled": False})
    backtest = safe_load_json(state_dir / "backtest_results.json", default={})
    quality_gate_passed = bool(backtest.get("quality_gate_passed", False))
    return {
        "enabled": bool(live_mode.get("enabled", False)),
        "quality_gate_passed": quality_gate_passed,
        "unlocked_at": live_mode.get("unlocked_at"),
        "backtest_summary": {
            "win_rate": backtest.get("win_rate"),
            "max_drawdown": backtest.get("max_drawdown"),
            "last_updated": backtest.get("last_updated"),
        },
    }


@app.post("/api/live-mode/unlock")
async def unlock_live_mode(req: LiveUnlockRequest):
    """Live 模式授權解鎖 — LIVE-02.
    需要雙重確認字串 + 品質閘門通過才能寫入 live_mode.json.
    Note: endpoint is localhost-only; future versions should add HTTPS/auth (T-10-05-02).
    """
    from scripts.etf_core import context as _ctx
    from scripts.etf_core.state_io import safe_load_json, atomic_save_json
    from datetime import datetime
    from zoneinfo import ZoneInfo

    # Server-side double-confirm enforcement (T-10-05-01)
    if req.confirm_1 != LIVE_CONFIRM_1 or req.confirm_2 != LIVE_CONFIRM_2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmation strings incorrect. "
                f"Required: confirm_1='{LIVE_CONFIRM_1}', "
                f"confirm_2='{LIVE_CONFIRM_2}'"
            ),
        )

    state_dir = _ctx.get_state_dir()
    # Re-check quality gate on every request (T-10-05-01)
    backtest = safe_load_json(state_dir / "backtest_results.json", default={})
    if not backtest.get("quality_gate_passed", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "Quality gate not passed. Run backtest_decision_outcomes.py first. "
                "Required: win_rate >= 0.5 and max_drawdown <= 0.15."
            ),
        )

    live_mode = {
        "enabled": True,
        "unlocked_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
        "unlocked_by": "dashboard",
        "quality_gate_passed_at_unlock": True,
    }
    atomic_save_json(state_dir / "live_mode.json", live_mode)
    return {"success": True, "enabled": True, "unlocked_at": live_mode["unlocked_at"]}
