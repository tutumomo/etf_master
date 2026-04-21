#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from scripts.ai_decision_bridge import build_ai_decision_request_from_state
from scripts.ai_decision_memory_context import build_decision_memory_context
from scripts.write_layered_review_plan import write_layered_review_plan
from market_calendar_tw import get_today_market_status


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _load_worldmonitor_alerts(state_dir: Path, hours: int = 2) -> list[dict]:
    """讀取最近 N 小時的 worldmonitor alerts"""
    from datetime import timezone, timedelta
    alerts_path = state_dir / 'worldmonitor_alerts.jsonl'
    if not alerts_path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = []
    try:
        for line in alerts_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ts_str = record.get('timestamp', '')
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    results.append(record)
            except Exception:
                continue
    except Exception:
        pass
    return results


def _resolve_wiki_roots() -> list[Path]:
    """回傳可用 wiki 根目錄（優先 profile wiki，再 fallback instance wiki）。"""
    candidates = [
        ROOT.parent.parent / 'wiki',
        ROOT / 'instances' / 'etf_master' / 'wiki',
    ]
    return [p for p in candidates if p.exists()]


def _read_first(paths: list[Path]) -> str:
    for p in paths:
        if p.exists():
            try:
                txt = p.read_text(encoding='utf-8').strip()
                if txt:
                    return txt
            except Exception:
                continue
    return ''


def _read_learned_rules(wiki_roots: list[Path]) -> str:
    """讀取 wiki/learned-rules.md，不存在或空回傳空字串（不阻斷）。"""
    paths = [root / "learned-rules.md" for root in wiki_roots]
    return _read_first(paths)


def _load_entity_wiki(entity_dirs: list[Path], symbol: str, limit: int = 800) -> str:
    if not symbol:
        return ''
    # exact file first, then slug-prefixed variant (e.g. 0050-yuanta-taiwan-50.md)
    for d in entity_dirs:
        exact = d / f'{symbol}.md'
        if exact.exists():
            try:
                return exact.read_text(encoding='utf-8')[:limit]
            except Exception:
                pass
        for p in sorted(d.glob(f'{symbol}-*.md')):
            try:
                txt = p.read_text(encoding='utf-8')
                if txt:
                    return txt[:limit]
            except Exception:
                continue
    return ''


def generate_request_payload_from_state_dir(state_dir: Path, requested_by: str = 'system', mode: str = 'decision_only') -> dict:
    strategy = _load_json(state_dir / 'strategy_link.json')
    positions = _load_json(state_dir / 'positions.json')
    orders_open = _load_json(state_dir / 'orders_open.json')
    fills_ledger = _load_json(state_dir / 'fills_ledger.json')
    portfolio_snapshot = _load_json(state_dir / 'portfolio_snapshot.json')
    market_cache = _load_json(state_dir / 'market_cache.json')
    market_intelligence = _load_json(state_dir / 'market_intelligence.json')
    intraday_tape_context = _load_json(state_dir / 'intraday_tape_context.json')
    market_context_taiwan = _load_json(state_dir / 'market_context_taiwan.json')
    market_event_context = _load_json(state_dir / 'market_event_context.json')
    market_calendar_payload = _load_json(state_dir / 'market_calendar_tw.json')
    reconciliation = _load_json(state_dir / 'filled_reconciliation.json')
    stock_intelligence = _load_json(state_dir / 'stock_intelligence.json')
    
    # 注入 Wiki 背景知識（profile wiki + instance wiki fallback）
    wiki_roots = _resolve_wiki_roots()
    concept_dirs = [p / 'concepts' for p in wiki_roots] + wiki_roots
    entity_dirs = [p / 'entities' for p in wiki_roots]
    
    # 計算持倉統計 (權重與成本)
    total_equity = float(portfolio_snapshot.get('total_equity', 0)) or 1.0
    portfolio_context = []
    for p in positions.get('positions', []):
        symbol = p.get('symbol')
        qty = float(p.get('quantity', 0))
        cost = float(p.get('average_cost', 0))
        current_p = float(market_cache.get('quotes', {}).get(symbol, {}).get('current_price', 0))
        weight = (qty * current_p / total_equity) * 100 if total_equity > 0 else 0
        bias = (current_p - cost) / cost * 100 if cost > 0 else 0
        portfolio_context.append({
            "symbol": symbol,
            "weight": f"{weight:.2f}%",
            "pnl_pct": f"{bias:.2f}%",
            "is_held": True
        })

    # 標記關注清單但未持有的標的
    watchlist_symbols = {item['symbol'] for item in _load_json(state_dir / 'watchlist.json').get('items', [])}
    held_symbols = {p.get('symbol') for p in positions.get('positions', [])}
    for sym in watchlist_symbols:
        if sym not in held_symbols:
            portfolio_context.append({"symbol": sym, "is_held": False, "note": "Watchlist only"})

    market_view_wiki = _read_first([
        d / 'market-view.md' for d in concept_dirs
    ])
    risk_signal_wiki = _read_first([
        d / 'risk-signal.md' for d in concept_dirs
    ])
    investment_strategies_wiki = _read_first([
        d / 'investment-strategies.md' for d in concept_dirs
    ])
    undervalued_ranking_wiki = _read_first([
        d / 'undervalued-etf-ranking.md' for d in concept_dirs
    ])
    
    # 為持有標的獲取 Wiki 摘要
    entity_wiki_summaries = {}
    for p in positions.get('positions', []):
        symbol = p.get('symbol')
        entity_txt = _load_entity_wiki(entity_dirs, symbol, limit=800)
        if entity_txt:
            entity_wiki_summaries[symbol] = entity_txt

    decision_memory_context = build_decision_memory_context(state_dir, limit=5)
    market_calendar_status = market_calendar_payload or get_today_market_status(datetime.now().astimezone(), market_calendar_payload)
    context_version = f"{strategy.get('base_strategy', 'unknown')}::{strategy.get('scenario_overlay', 'unknown')}"

    worldmonitor_snapshot = _load_json(state_dir / 'worldmonitor_snapshot.json')
    worldmonitor_alerts = _load_worldmonitor_alerts(state_dir, hours=2)

    payload = build_ai_decision_request_from_state(
        strategy=strategy,
        positions=positions,
        orders_open=orders_open,
        fills_ledger=fills_ledger,
        portfolio_snapshot=portfolio_snapshot,
        market_cache=market_cache,
        market_intelligence=market_intelligence,
        intraday_tape_context=intraday_tape_context,
        market_context_taiwan=market_context_taiwan,
        market_event_context=market_event_context,
        market_calendar_status=market_calendar_status,
        reconciliation=reconciliation,
        decision_memory_context=decision_memory_context,
        worldmonitor_snapshot=worldmonitor_snapshot,
        worldmonitor_alerts=worldmonitor_alerts,
        requested_by=requested_by,
        mode=mode,
        context_version=context_version,
    )
    # 合併額外背景知識
    payload['portfolio_context'] = portfolio_context
    payload['wiki_context'] = {
        "market_view": market_view_wiki,
        "risk_signal": risk_signal_wiki,
        "investment_strategies": investment_strategies_wiki,
        "undervalued_ranking": undervalued_ranking_wiki,
        "entities": entity_wiki_summaries,
        "learned_rules": _read_learned_rules(wiki_roots),
    }
    payload['stock_intelligence'] = stock_intelligence
    (state_dir / 'ai_decision_request.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    write_layered_review_plan(state_dir, payload.get('request_id', 'missing-request-id'))
    return payload


if __name__ == '__main__':
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / 'instances' / 'etf_master' / 'state')
    payload = generate_request_payload_from_state_dir(target_dir)
    print(json.dumps({"ok": True, "request_id": payload.get('request_id')}, ensure_ascii=False))
