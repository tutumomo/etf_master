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
    
    # 注入 Wiki 背景知識
    wiki_path = ROOT.parent.parent / 'docs' / 'wiki' / 'shioaji'
    
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

    market_view_wiki = ""
    if (wiki_path / 'concepts' / 'market-view.md').exists():
        market_view_wiki = (wiki_path / 'concepts' / 'market-view.md').read_text(encoding='utf-8')
    
    # 為持有標的獲取 Wiki 摘要
    entity_wiki_summaries = {}
    for p in positions.get('positions', []):
        symbol = p.get('symbol')
        wiki_file = wiki_path / 'entities' / f"{symbol}.md"
        if wiki_file.exists():
            entity_wiki_summaries[symbol] = wiki_file.read_text(encoding='utf-8')[:500] # 限制長度

    decision_memory_context = build_decision_memory_context(state_dir, limit=5)
    market_calendar_status = market_calendar_payload or get_today_market_status(datetime.now().astimezone(), market_calendar_payload)
    context_version = f"{strategy.get('base_strategy', 'unknown')}::{strategy.get('scenario_overlay', 'unknown')}"

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
        requested_by=requested_by,
        mode=mode,
        context_version=context_version,
    )
    # 合併額外背景知識
    payload['portfolio_context'] = portfolio_context
    payload['wiki_context'] = {
        "market_view": market_view_wiki,
        "entities": entity_wiki_summaries
    }
    payload['stock_intelligence'] = stock_intelligence
    (state_dir / 'ai_decision_request.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    write_layered_review_plan(state_dir, payload.get('request_id', 'missing-request-id'))
    return payload


if __name__ == '__main__':
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / 'instances' / 'etf_master' / 'state')
    payload = generate_request_payload_from_state_dir(target_dir)
    print(json.dumps({"ok": True, "request_id": payload.get('request_id')}, ensure_ascii=False))
