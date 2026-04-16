#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context
from state_reconciliation import reconciliation_summary

STATE = context.get_state_dir()
AGENT_STRATEGY = context.get_instance_dir() / "strategy_state.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    strict = "--strict" in sys.argv
    print(f"=== ETF_TW Alignment Diagnostic [{datetime.now().isoformat()}] ===")
    
    # 1. Trading Mode
    mode = load_json(STATE / "trading_mode.json")
    print(f"[Mode] Effective: {mode.get('effective_mode')} | Health: {'OK' if mode.get('health_check_ok') else 'FAIL'}")

    # ROOT_STATE_SENSITIVE_GUARD
    root_state = context.get_state_dir()
    sensitive = [
        'positions.json','account_snapshot.json','orders_open.json','portfolio_snapshot.json','agent_summary.json',
        'strategy_link.json','trading_mode.json','watchlist.json','intraday_tape_context.json'
    ]
    present = [name for name in sensitive if (root_state / name).exists()]
    if present:
        print(f"[Root State Guard] ⚠️ sensitive files present in root state: {present}")
        if strict:
            raise SystemExit(2)

    
    # 2. Strategy
    dash_strat = load_json(STATE / "strategy_link.json")
    agent_strat = load_json(AGENT_STRATEGY)
    
    print(f"[Strategy Check]")
    print(f"  Dashboard: {dash_strat.get('base_strategy')} / {dash_strat.get('scenario_overlay')}")
    print(f"  Agent    : {agent_strat.get('base_strategy')} / {agent_strat.get('scenario_overlay')}")
    
    match = (dash_strat.get('base_strategy') == agent_strat.get('base_strategy') and 
             dash_strat.get('scenario_overlay') == agent_strat.get('scenario_overlay'))
    print(f"  Alignment: {'✅ MATCH' if match else '❌ DRIFT DETECTED'}")
    
    # 3. Market Data
    cache = load_json(STATE / "market_cache.json")
    count = len(cache.get("quotes", {}))
    has_prices = any(q.get("current_price", 0) > 0 for q in cache.get("quotes", {}).values())
    print(f"[Market Data] Symbols: {count} | Data Quality: {'✅ PRICE_OK' if has_prices else '❌ MISSING_PRICES'}")
    
    # 4. Tape Context
    tape = load_json(STATE / "intraday_tape_context.json")
    print(f"[Tape Context] Market Bias: {tape.get('market_bias')} | Last Fresh: {tape.get('updated_at')}")

    # 5. State Reconciliation
    positions = load_json(STATE / "positions.json")
    snapshot = load_json(STATE / "portfolio_snapshot.json")
    orders_open = load_json(STATE / "orders_open.json")
    recon = reconciliation_summary(positions, snapshot, orders_open)
    print(f"[State Reconciliation] Positions/Snapshot: {'✅ MATCH' if recon.get('positions_vs_snapshot_match') else '❌ DRIFT'} | Open-not-in-positions: {recon.get('open_orders_not_in_positions')} | Snapshot Lag(sec): {recon.get('snapshot_lag_sec')}")

    if match and has_prices and recon.get('positions_vs_snapshot_match'):
        print("\nOVERALL STATUS: ✅ ALL SYSTEMS ALIGNED")
    else:
        print("\nOVERALL STATUS: ⚠️ PARTIAL ALIGNMENT (Check details above)")


if __name__ == "__main__":
    main()
