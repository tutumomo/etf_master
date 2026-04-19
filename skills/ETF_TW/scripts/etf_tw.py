#!/usr/bin/env python3
"""
ETF_TW CLI - Taiwan ETF investing assistant with multi-broker support.

Supports:
- ETF list, search, category filter
- ETF comparison and DCA calculation
- Order preview, validation, paper trading
- Multi-broker, multi-account architecture (Phase 4)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import subprocess
from pathlib import Path
from typing import Optional

# Import existing modules
from beginner_flow import beginner_topic
from calc_dca import calculate_dca
from compare_etf import compare_etfs
from paper_trade import execute_paper_trade
from preview_order import preview_order
from validate_order import validate_order

# Import new account manager
from account_manager import get_account_manager, AccountManager
from adapters.base import Order
from trading_mode import read_trading_mode_state, write_trading_mode_state, resolve_effective_mode
from truth_level import format_with_level, LEVEL_1_LIVE, LEVEL_2_VERIFYING, LEVEL_3_SNAPSHOT

ROOT = Path(__file__).resolve().parents[1]
ETF_CURATED_PATH = ROOT / "data" / "etfs.json"              # curated subset (rich metadata)
ETF_UNIVERSE_PATH = ROOT / "data" / "etf_universe_tw.json"  # full tradable universe (TWSE + TPEx)
BROKER_PATH = ROOT / "data" / "brokers.json"
SAMPLE_ORDERS_PATH = ROOT / "data" / "sample_orders.json"
LEDGER_PATH = ROOT / "data" / "paper_ledger.json"


def _normalize_etf_item(symbol: str, item: dict) -> dict:
    out = dict(item)
    out["symbol"] = symbol
    # Map aliases for compatibility with code that uses different names
    if "description" in out and "summary" not in out:
        out["summary"] = out["description"]
    if "summary" not in out:
        out["summary"] = out.get("name", symbol)
    if "dividend_frequency" in out and "distribution_frequency" not in out:
        out["distribution_frequency"] = out["dividend_frequency"]
    if "index" in out and "focus" not in out:
        out["focus"] = out["index"]
    return out


def _load_etf_map(path: Path) -> dict:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("etfs") or {}


def load_etfs() -> list[dict]:
    """Load ETF metadata.

    - Universe (tradable set) comes from ETF_UNIVERSE_PATH.
    - Curated metadata overlays on top (expense ratio, category, distribution, etc.).

    This allows validation/preview to accept any listed ETF symbol while still keeping rich
    metadata for the core watchlist.
    """
    universe = _load_etf_map(ETF_UNIVERSE_PATH)
    curated = _load_etf_map(ETF_CURATED_PATH)

    merged: dict[str, dict] = {}
    for sym, item in universe.items():
        merged[sym] = dict(item)
    for sym, item in curated.items():
        merged[sym] = {**merged.get(sym, {}), **dict(item)}

    result = [_normalize_etf_item(sym, item) for sym, item in merged.items()]
    return result


def load_brokers() -> list[dict]:
    data = json.loads(BROKER_PATH.read_text(encoding="utf-8"))["brokers"]
    return [{"broker_id": k, **v} for k, v in data.items()]


def load_orders(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "orders" in payload:
        return payload["orders"]
    if isinstance(payload, list):
        return payload
    raise ValueError("unsupported order file format")


def normalize_order_payload(order: dict):
    """Convert a dict order into the adapter Order dataclass shape."""
    side = str(order.get("side") or order.get("action") or "buy").lower()
    order_type = str(order.get("order_type") or "market").lower()
    lot_type = str(order.get("lot_type") or ("board" if int(order.get("quantity") or 0) >= 1000 else "odd")).lower()
    mode = str(order.get("mode") or "paper").lower()
    return Order(
        symbol=str(order.get("symbol") or "").upper(),
        action=side,
        quantity=int(order.get("quantity") or 0),
        price=order.get("price"),
        order_type=order_type,
        account_id=order.get("account"),
        broker_id=order.get("broker"),
        mode=mode,
    )


def known_symbols() -> set[str]:
    # Use universe keys as the primary tradable symbol set.
    universe = _load_etf_map(ETF_UNIVERSE_PATH)
    if universe:
        return set(universe.keys())
    # Fallback: curated set only.
    return {etf["symbol"] for etf in load_etfs()}


async def evaluate_pre_flight_gate(adapter, normalized_order: Order) -> dict:
    """Run unified pre-flight gate using live account balance/positions context.

    This keeps preview/validate/submit-preview consistent with the real submit path.
    """
    try:
        from scripts.pre_flight_gate import check_order
    except ImportError:
        from pre_flight_gate import check_order

    try:
        from scripts.etf_core import context as etf_context
    except ImportError:
        from etf_core import context as etf_context

    context = {
        'cash': 0.0,
        'max_concentration_pct': getattr(adapter, 'config', {}).get('max_concentration_pct', 0.3),
        'max_single_limit_twd': getattr(adapter, 'config', {}).get('max_single_limit_twd', 500000.0),
        'risk_temperature': getattr(adapter, 'config', {}).get('risk_temperature', 1.0),
        'force_trading_hours': getattr(adapter, 'config', {}).get('force_trading_hours', True),
        'inventory': {},
        'current_holding_value': 0.0,
        'total_portfolio_value': 0.0,
        'state_dir': etf_context.get_state_dir(),
    }

    try:
        account_id = normalized_order.account_id or ""
        balance = await adapter.get_account_balance(account_id)
        context['cash'] = float(getattr(balance, 'cash_available', 0) or 0)
        context['total_portfolio_value'] = float(getattr(balance, 'total_value', 0) or 0)

        positions = await adapter.get_positions(account_id)
        context['inventory'] = {getattr(p, 'symbol', ''): float(getattr(p, 'quantity', 0) or 0) for p in positions}
        for p in positions:
            if getattr(p, 'symbol', '') == normalized_order.symbol:
                context['current_holding_value'] = float(getattr(p, 'market_value', 0) or 0)
                break
    except Exception as e:
        # Keep behavior safe: if account context retrieval fails, surface as gate failure.
        return {
            'passed': False,
            'reason': 'preflight_context_unavailable',
            'details': {'error': str(e)},
        }

    lot_type = 'board' if normalized_order.quantity >= 1000 else 'odd'
    order_dict = {
        'symbol': normalized_order.symbol,
        'side': normalized_order.action,
        'quantity': normalized_order.quantity,
        'price': normalized_order.price or 0.0,
        'order_type': normalized_order.order_type,
        'lot_type': lot_type,
        'is_submit': False,
        'is_confirmed': False,
    }
    return check_order(order_dict, context)


def cmd_universe_sync() -> int:
    """Update the tradable ETF universe file."""
    script = ROOT / "scripts" / "sync_etf_universe_tw.py"
    # Use venv python if present for consistent deps, otherwise fall back to current python.
    venv_py = ROOT / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    proc = subprocess.run([py, str(script)], cwd=str(ROOT))
    return int(proc.returncode)


def _load_universe_payload() -> dict:
    if not ETF_UNIVERSE_PATH.exists():
        return {"meta": {}, "etfs": {}}
    return json.loads(ETF_UNIVERSE_PATH.read_text(encoding="utf-8"))


def cmd_universe_list(args) -> int:
    payload = _load_universe_payload()
    etfs = payload.get("etfs") or {}
    items = []
    for sym, item in etfs.items():
        if args.exchange and str(item.get("exchange") or "").upper() != args.exchange.upper():
            continue
        items.append((sym, item))
    items.sort(key=lambda x: x[0])

    limit = int(args.limit or 50)
    print(f"ETF universe: {len(items)} items" + (f" (exchange={args.exchange})" if args.exchange else ""))
    print("symbol\texchange\tname\tissuer")
    for sym, item in items[:limit]:
        print(f"{sym}\t{item.get('exchange','')}\t{item.get('name','')}\t{item.get('issuer','')}")
    if len(items) > limit:
        print(f"... truncated, showing {limit}/{len(items)}")
    return 0


def cmd_universe_search(args) -> int:
    q = (args.query or "").strip()
    if not q:
        print("query is required")
        return 2
    payload = _load_universe_payload()
    etfs = payload.get("etfs") or {}

    q_lower = q.lower()
    hits = []
    for sym, item in etfs.items():
        name = str(item.get("name") or "")
        if q_lower in sym.lower() or q_lower in name.lower():
            hits.append((sym, item))
    hits.sort(key=lambda x: x[0])

    print(f"hits: {len(hits)}")
    for sym, item in hits[: int(args.limit or 50)]:
        print(f"{sym}\t{item.get('exchange','')}\t{item.get('name','')}")
    return 0


def cmd_universe_show(args) -> int:
    sym = (args.symbol or "").strip()
    if not sym:
        print("symbol is required")
        return 2

    payload = _load_universe_payload()
    universe = payload.get("etfs") or {}
    curated = _load_etf_map(ETF_CURATED_PATH)

    base = universe.get(sym)
    if not base:
        print(f"not found in universe: {sym}")
        return 1

    merged = {**dict(base), **dict(curated.get(sym, {}))}
    merged["symbol"] = sym
    print(json.dumps(merged, ensure_ascii=False, indent=2))
    return 0


def find_etf(symbol: str) -> dict | None:
    symbol = symbol.upper()
    for etf in load_etfs():
        if etf["symbol"].upper() == symbol:
            return etf
    return None


# ==================== Account Management Commands ====================

def cmd_list_accounts(args: argparse.Namespace) -> int:
    """List all configured accounts."""
    manager = get_account_manager()
    accounts = manager.list_accounts()
    
    if not accounts:
        print("尚未配置任何帳戶")
        return 1
    
    print("已配置的帳戶：")
    print("=" * 72)
    for acc in accounts:
        prefix = "*" if acc.get('is_default') else "  "
        default_label = " (預設)" if acc.get('is_default') else ""
        print(f"{prefix} 別名：{acc['alias']}{default_label}")
        print(f"    券商：{acc['broker_id']}")
        print(f"    帳號：{acc['account_id']}")
        print(f"    模式：{acc['mode']}")
        if acc.get('description'):
            print(f"    說明：{acc['description']}")
        print()
    
    return 0


def cmd_list_brokers(args: argparse.Namespace) -> int:
    """List all available brokers."""
    manager = get_account_manager()
    brokers = manager.list_brokers()
    
    if not brokers:
        print("無券商資料")
        return 1
    
    print("支援的券商：")
    print("=" * 72)
    for broker in brokers:
        print(f"代號：{broker['broker_id']}")
        print(f"  名稱：{broker.get('name', broker.get('name_en', 'Unknown'))}")
        print(f"  類型：{broker['type']}")
        print(f"  支援模式：paper={broker.get('supports_paper', False)}, "
              f"sandbox={broker.get('supports_sandbox', False)}, "
              f"live={broker.get('supports_live', False)}")
        print()
    
    return 0


async def cmd_broker_health(args: argparse.Namespace) -> int:
    """Run broker/account health checks without submitting orders."""
    account_alias = args.account
    try:
        manager = get_account_manager()
        adapter = manager.get_adapter(account_alias)
        account = manager.get_account(account_alias)
        
        print("Broker health check")
        print("=" * 72)
        print(f"帳戶別名：{account.get('alias', account_alias or 'default')}")
        print(f"券商：{account.get('broker_id')}")
        print(f"帳號：{account.get('account_id')}")
        print(f"模式：{account.get('mode')}")
        
        ok = await adapter.authenticate()
        print(f"登入：{'[OK]' if ok else '[失敗]'}")
        if not ok:
            return 1
        
        try:
            balance = await adapter.get_account_balance(account.get('account_id'))
            print(f"帳務：OK | 可用資金={getattr(balance, 'cash_available', 0):,.2f} | 總資產={getattr(balance, 'total_value', 0):,.2f}")
        except Exception as e:
            print(f"帳務：FAIL | {e}")
            return 1
        
        try:
            positions = await adapter.get_positions(account.get('account_id'))
            print(f"持倉：OK | {len(positions)} 筆")
        except Exception as e:
            print(f"持倉：FAIL | {e}")
            return 1
        
        return 0
    except Exception as e:
        print(f"錯誤：{e}")
        return 1


async def cmd_preview_account(args: argparse.Namespace) -> int:
    """Preview order with account routing."""
    account_alias = args.account
    file_path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH
    
    try:
        manager = get_account_manager()
        adapter = manager.get_adapter(account_alias)
        
        # Authenticate
        if not await adapter.authenticate():
            print(f"帳戶 {account_alias or 'default'} 認證失敗")
            return 1
        
        # Load orders
        orders = load_orders(file_path)
        symbols = known_symbols()
        
        results = []
        for index, order in enumerate(orders, start=1):
            # Validate
            config = manager.get_config()
            validation_result = validate_order(order, symbols, config)
            if not validation_result["valid"]:
                results.append({
                    "index": index,
                    "order": order,
                    "validation": validation_result,
                    "status": "invalid"
                })
                continue
            
            normalized_order = normalize_order_payload(order)
            
            # Preview + pre-flight gate（帳戶餘額/持倉風控）
            preview_result = await adapter.preview_order(normalized_order)
            gate_result = await evaluate_pre_flight_gate(adapter, normalized_order)
            results.append({
                "index": index,
                "order": order,
                "preview": preview_result.__dict__ if hasattr(preview_result, '__dict__') else preview_result,
                "pre_flight_gate": gate_result,
                "status": "previewed" if gate_result.get("passed", False) else "blocked_by_gate"
            })
        
        # Output results
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0
        
    except Exception as e:
        print(f"錯誤：{e}")
        return 1


async def cmd_validate_account(args: argparse.Namespace) -> int:
    """Validate order with account routing."""
    account_alias = args.account
    file_path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH
    
    try:
        manager = get_account_manager()
        adapter = manager.get_adapter(account_alias)
        
        # Authenticate
        if not await adapter.authenticate():
            print(f"帳戶 {account_alias or 'default'} 認證失敗")
            return 1
        
        # Load orders
        orders = load_orders(file_path)
        symbols = known_symbols()
        
        results = []
        for index, order in enumerate(orders, start=1):
            normalized_order = normalize_order_payload(order)
            is_valid, warnings = await adapter.validate_order(normalized_order)
            gate_result = await evaluate_pre_flight_gate(adapter, normalized_order)
            combined_valid = bool(is_valid) and bool(gate_result.get("passed", False))
            combined_warnings = list(warnings or [])
            if not gate_result.get("passed", False):
                combined_warnings.append(f"pre-flight gate blocked: {gate_result.get('reason')}")
            results.append({
                "index": index,
                "order": order,
                "valid": combined_valid,
                "warnings": combined_warnings,
                "pre_flight_gate": gate_result
            })
        
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0
        
    except Exception as e:
        print(f"錯誤：{e}")
        return 1


async def cmd_submit_preview(args: argparse.Namespace) -> int:
    """Final confirmation checklist before live submit."""
    account_alias = args.account
    file_path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH

    try:
        manager = get_account_manager()
        account = manager.get_account(account_alias)
        adapter = manager.get_adapter(account_alias)

        if not await adapter.authenticate():
            print(f"帳戶 {account_alias or 'default'} 認證失敗")
            return 1

        orders = load_orders(file_path)
        config = manager.get_config()
        symbols = known_symbols()

        results = []
        for index, order in enumerate(orders, start=1):
            validation = validate_order(order, symbols, config)
            normalized_order = normalize_order_payload(order)
            preview = await adapter.preview_order(normalized_order)
            gate_result = await evaluate_pre_flight_gate(adapter, normalized_order)
            order_value = float((normalized_order.price or getattr(preview, 'price', 0) or 0) * normalized_order.quantity)
            fee = float(getattr(preview, 'fee', 0) or 0)
            tax = float(getattr(preview, 'tax', 0) or 0)
            total_cost = order_value + fee + tax
            lot_unit = '張' if normalized_order.quantity % 1000 == 0 else '股'
            validation_errors = list(validation.get('errors', []))
            validation_warnings = list(validation.get('warnings', []))
            if not gate_result.get('passed', False):
                validation_errors.append(f"pre-flight gate blocked: {gate_result.get('reason')}")

            checklist = {
                'account_alias': account.get('alias', account_alias),
                'broker_id': account.get('broker_id'),
                'account_id': account.get('account_id'),
                'mode': account.get('mode'),
                'symbol': normalized_order.symbol,
                'side': normalized_order.action,
                'lot_unit': lot_unit,
                'quantity': normalized_order.quantity,
                'price': normalized_order.price or getattr(preview, 'price', None),
                'order_value': round(order_value, 2),
                'fee': round(fee, 2),
                'tax': round(tax, 2),
                'total_cost': round(total_cost, 2),
                'validation': {
                    'valid': bool(validation.get('valid', False)) and bool(gate_result.get('passed', False)),
                    'errors': validation_errors,
                    'warnings': validation_warnings,
                },
                'pre_flight_gate': gate_result,
                'preview_status': getattr(preview, 'status', 'preview'),
                'warnings': validation_warnings,
            }
            results.append({'index': index, 'submit_preview': checklist})

        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as e:
        print(f"錯誤：{e}")
        return 1


async def cmd_paper_account(args: argparse.Namespace) -> int:
    """Execute paper trade with account routing."""
    account_alias = args.account
    file_path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH
    
    try:
        manager = get_account_manager()
        adapter = manager.get_adapter(account_alias)
        
        # Authenticate
        if not await adapter.authenticate():
            print(f"帳戶 {account_alias or 'default'} 認證失敗")
            return 1
        
        # Load orders
        orders = load_orders(file_path)
        symbols = known_symbols()
        
        results = []
        for index, order in enumerate(orders, start=1):
            # Validate
            config = manager.get_config()
            validation_result = validate_order(order, symbols, config)
            if not validation_result["valid"]:
                results.append({
                    "index": index,
                    "order": order,
                    "validation": validation_result,
                    "status": "invalid"
                })
                continue
            
            # Submit order
            submitted_order = await adapter.submit_order(order)
            order_res = submitted_order.__dict__ if hasattr(submitted_order, '__dict__') else submitted_order
            
            # Add truth level verification message
            if isinstance(order_res, dict) and order_res.get('status') == 'submitted':
                order_res['verification'] = "[驗證中] 委託已送出，仍需後續驗證（list_trades）確認落地事實"

            results.append({
                "index": index,
                "order": order,
                "result": order_res,
                "status": "submitted"
            })
        
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0
        
    except Exception as e:
        print(f"錯誤：{e}")
        return 1


# ==================== Original Commands (kept for compatibility) ====================

def cmd_list(_: argparse.Namespace) -> int:
    print("台灣 ETF 清單")
    print("=" * 72)
    for etf in load_etfs():
        print(f"{etf['symbol']:8} {etf['name']:12} {etf['category']:15} {etf['summary']}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    keyword = args.keyword.lower()
    results = [
        etf for etf in load_etfs()
        if keyword in etf["symbol"].lower() or keyword in etf["name"].lower() or keyword in etf["summary"].lower()
    ]
    if not results:
        print(f"找不到符合關鍵字：{args.keyword}")
        return 1
    for etf in results:
        print(f"{etf['symbol']} {etf['name']} | {etf['category']} | {etf['summary']}")
    return 0


def cmd_category(args: argparse.Namespace) -> int:
    category = args.category.lower()
    results = [etf for etf in load_etfs() if etf["category"].lower() == category]
    if not results:
        print(f"找不到類別：{args.category}")
        return 1
    for etf in results:
        print(f"{etf['symbol']} {etf['name']} | {etf['summary']}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    left = find_etf(args.symbol1)
    right = find_etf(args.symbol2)
    if not left or not right:
        print("比較失敗：至少有一個 ETF 代碼不存在。")
        return 1
    comparison = compare_etfs(left, right)
    print(f"比較 {left['symbol']} {left['name']} vs {right['symbol']} {right['name']}")
    print("=" * 72)
    print(f"類別：{left['category']} | {right['category']}")
    print(f"配息：{left['distribution_frequency']} | {right['distribution_frequency']}")
    print(f"費用率：{left['expense_ratio']:.2f}% | {right['expense_ratio']:.2f}%")
    print(f"風險：{left['risk_level']} | {right['risk_level']}")
    print(f"適合：{', '.join(left['suitable_for'])} | {', '.join(right['suitable_for'])}")
    print(f"摘要：{left['summary']} | {right['summary']}")
    print("重點：")
    for item in comparison["highlights"]:
        print(f"- {item}")
    return 0


def cmd_calc(args: argparse.Namespace) -> int:
    etf = find_etf(args.symbol)
    if not etf:
        print(f"找不到 ETF：{args.symbol}")
        return 1
    result = calculate_dca(args.amount, args.years, args.annual_return)
    print(f"定期定額試算：{etf['symbol']} {etf['name']}")
    print("=" * 72)
    print(f"每月投入：NT$ {result['monthly_amount']:,.0f}")
    print(f"投資年數：{result['years']} 年（{result['months']} 個月）")
    print(f"假設年化報酬：{result['assumed_annual_return'] * 100:.2f}%")
    print(f"投入本金：NT$ {result['principal']:,.2f}")
    print(f"預估期末資產：NT$ {result['projected_value']:,.2f}")
    print(f"預估資本利得：NT$ {result['estimated_gain']:,.2f}")
    print("注意：此為固定報酬率假設試算，不代表實際投資結果。")
    return 0


def cmd_guide(args: argparse.Namespace) -> int:
    brokers = load_brokers()
    topic = args.topic
    if topic == "account":
        print("台灣證券開戶基本流程")
        print("1. 選券商 2. 準備證件與本人銀行帳戶 3. 開立證券戶與交割戶 4. 完成審核後再做首次入金")
        return 0
    if topic == "discount":
        print("券商與費用提醒")
        for broker in brokers:
            print(f"- {broker['name']}: {broker['fee_notes']}")
        return 0
    if topic == "docs":
        print("常見開戶文件：身分證、第二證件、本人銀行帳戶資料。")
        return 0
    if topic == "tax":
        print("ETF 賣出交易稅通常為 0.1%，另有券商手續費；實際仍以券商公告為準。")
        return 0
    print("可用 guide 主題：account / discount / docs / tax")
    return 1


def cmd_beginner(args: argparse.Namespace) -> int:
    try:
        print(beginner_topic(args.topic))
        return 0
    except KeyError:
        print("可用 beginner 主題：basics / choose-style / first-trade / pitfalls / risk")
        return 1


def cmd_preview_order(args: argparse.Namespace) -> int:
    path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH
    orders = load_orders(path)
    symbols = known_symbols()
    exit_code = 0
    for index, order in enumerate(orders, start=1):
        result = validate_order(order, symbols)
        print(json.dumps({"index": index, "order": order, "validation": result}, ensure_ascii=False, indent=2))
        if not result["valid"]:
            exit_code = 1
    return exit_code


def cmd_validate_order(args: argparse.Namespace) -> int:
    path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH
    orders = load_orders(path)
    symbols = known_symbols()
    exit_code = 0
    try:
        manager = get_account_manager()
        config = manager.get_config()
    except:
        config = {}
        
    for index, order in enumerate(orders, start=1):
        result = validate_order(order, symbols, config)
        print(json.dumps({"index": index, "order": order, "validation": result}, ensure_ascii=False, indent=2))
        if not result["valid"]:
            exit_code = 1
    return exit_code


def cmd_paper_trade(args: argparse.Namespace) -> int:
    symbols = known_symbols()
    
    # Check if manual order provided
    if args.symbol:
        order = {
            "symbol": args.symbol,
            "side": args.side or "buy",
            "quantity": args.quantity or 100,
            "price": args.price,
            "order_type": "limit" if args.price else "market",
            "lot_type": "board" if (args.quantity or 100) >= 1000 else "odd",
            "mode": "paper"
        }
        orders = [order]
    else:
        path = Path(args.file) if args.file else SAMPLE_ORDERS_PATH
        orders = load_orders(path)
        
    try:
        manager = get_account_manager()
        config = manager.get_config()
    except:
        config = {}
        
    exit_code = 0
    for index, order in enumerate(orders, start=1):
        validation = validate_order(order, symbols, config)
        if not validation["valid"]:
            print(json.dumps({"index": index, "order": order, "validation": validation}, ensure_ascii=False, indent=2))
            exit_code = 1
            continue
        etf = find_etf(order["symbol"])
        preview = preview_order(order, etf)
        trade = execute_paper_trade(order, preview, LEDGER_PATH)
        print(json.dumps({"index": index, "paper_trade": trade}, ensure_ascii=False, indent=2))
    return exit_code


def cmd_portfolio(_: argparse.Namespace) -> int:
    """Calculate and display portfolio performance."""
    if not LEDGER_PATH.exists():
        print("尚未有交易紀錄。")
        return 0
        
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    trades = ledger.get("trades", [])
    
    if not trades:
        print("模擬帳本為空。")
        return 0
        
    holdings = {} # symbol -> {quantity, cost, realized_pnl}
    
    for t in trades:
        sym = t["symbol"]
        if sym not in holdings:
            holdings[sym] = {"quantity": 0, "cost": 0.0, "realized_pnl": 0.0}
            
        q = t["quantity"]
        p = t["price"] or 0.0 # Use 0 for market orders if price unknown
        cost_inc = t.get("estimated_total_cost", q * p)
        
        if t["side"] == "buy":
            holdings[sym]["quantity"] += q
            holdings[sym]["cost"] += cost_inc
        elif t["side"] == "sell":
            if holdings[sym]["quantity"] > 0:
                avg_cost = holdings[sym]["cost"] / holdings[sym]["quantity"]
                holdings[sym]["realized_pnl"] += (cost_inc - (avg_cost * q))
                holdings[sym]["quantity"] -= q
                holdings[sym]["cost"] -= avg_cost * q
                
    # Fetch current prices for unrealized pnl
    current_prices = {}
    try:
        import yfinance as yf
        symbols_to_fetch = [s for s, h in holdings.items() if h["quantity"] > 0]
        if symbols_to_fetch:
            tickers = " ".join([f"{s}.TW" for s in symbols_to_fetch])
            data = yf.download(tickers, period="1d", progress=False)
            if not data.empty:
                for s in symbols_to_fetch:
                    ticker = f"{s}.TW"
                    if ticker in data["Close"]:
                        price = data["Close"][ticker].iloc[-1]
                        if not np.isnan(price):
                            current_prices[s] = price
    except Exception:
        pass # Fallback to 0 or last known
        
    mode_state = read_trading_mode_state()
    effective_mode = (mode_state.get("effective_mode") or "paper").lower()
    truth_level = LEVEL_1_LIVE if "live" in effective_mode else LEVEL_3_SNAPSHOT
    title = format_with_level("報表] 模擬投資組合概覽", truth_level) if "live" not in effective_mode else format_with_level("報表] 即時投資組合概覽", truth_level)

    print(f"\n{title}")
    print("=" * 80)
    print(f"{'代碼':8} {'持股':>8} {'平均成本':>10} {'現價':>10} {'市值':>12} {'未實現損益':>12} {'報酬率':>8}")
    print("-" * 80)
    
    total_cost = 0.0
    total_market_value = 0.0
    total_realized_pnl = 0.0
    
    for sym, h in holdings.items():
        total_realized_pnl += h["realized_pnl"]
        if h["quantity"] <= 0:
            continue
            
        avg_price = h["cost"] / h["quantity"]
        curr_price = current_prices.get(sym, avg_price) # Fallback to cost if no price
        market_value = h["quantity"] * curr_price
        unrealized = market_value - h["cost"]
        roi = (unrealized / h["cost"]) * 100 if h["cost"] > 0 else 0
        
        total_cost += h["cost"]
        total_market_value += market_value
        
        print(f"{sym:8} {h['quantity']:>8,d} {avg_price:>10.2f} {curr_price:>10.2f} {market_value:>12.2f} {unrealized:>12.2f} {roi:>7.2f}%")
        
    print("-" * 80)
    total_pnl = (total_market_value - total_cost) + total_realized_pnl
    total_roi = (total_pnl / (total_cost or 1)) * 100
    
    print(f"總投入成本：NT$ {total_cost:,.2f}")
    print(f"目前總市值：NT$ {total_market_value:,.2f}")
    print(f"累計實現損益：NT$ {total_realized_pnl:,.2f}")
    print(f"總損益 (含未實現)：NT$ {total_pnl:,.2f}")
    print(f"總報酬率：{total_roi:.2f}%")
    return 0


async def cmd_orders(args: argparse.Namespace) -> int:
    """List open or recent orders with truth level labeling."""
    manager = get_account_manager()
    account_alias = args.account
    try:
        adapter = manager.get_adapter(account_alias)
        account = manager.get_account(account_alias)
        
        if not await adapter.authenticate():
            print(f"帳戶 {account_alias or 'default'} 認證失敗")
            return 1
            
        trades = await adapter.list_trades()
        
        mode = account.get('mode', 'paper').lower()
        truth_level = LEVEL_1_LIVE if mode == 'live' else LEVEL_3_SNAPSHOT
        title = format_with_level("委託清單 (Orders)", truth_level)
        
        print(f"\n{title}")
        print("=" * 100)
        print(f"{'代碼':8} {'動作':4} {'數量':10} {'價格':10} {'狀態':15} {'委託序號'}")
        print("-" * 100)
        
        for t in trades:
            if hasattr(t, 'status') and hasattr(t, 'order'): # Shioaji Trade object
                symbol = getattr(getattr(t, 'contract', None), 'code', 'unknown')
                action = "買進" if getattr(t.order, 'action', '') == 'Buy' else "賣出"
                quantity = getattr(t.order, 'quantity', 0) * 1000
                price = getattr(t.order, 'price', 0)
                status = getattr(t.status, 'status', 'unknown')
                order_id = getattr(t.status, 'order_id', 'unknown')
            elif hasattr(t, 'symbol'): # Order dataclass (Paper adapter)
                symbol = t.symbol
                action = "買進" if t.action == 'buy' else "賣出"
                quantity = t.quantity
                price = t.price or 0.0
                status = t.status
                order_id = getattr(t, 'order_id', 'paper_id')
            else:
                continue
            print(f"{symbol:8} {action:4} {quantity:10,d} {price:10.2f} {status:15} {order_id}")
        return 0
    except Exception as e:
        print(f"錯誤：{e}")
        return 1


async def cmd_list_trades(args: argparse.Namespace) -> int:
    """List historical trades with truth level labeling."""
    # Alias for cmd_orders for now, but can be specialized for filled ones
    return await cmd_orders(args)


def get_mini_summary() -> str:
    """Get a 1-line summary for welcome message."""
    if not LEDGER_PATH.exists(): return ""
    try:
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        trades = ledger.get("trades", [])
        if not trades: return ""
        
        holdings = {}
        for t in trades:
            sym = t["symbol"]
            q = t["quantity"]
            if t["side"] == "buy":
                holdings[sym] = holdings.get(sym, 0) + q
            else:
                holdings[sym] = holdings.get(sym, 0) - q
        
        active_counts = sum(1 for q in holdings.values() if q > 0)
        return f"💡 歡迎回來！您目前持倉 {active_counts} 檔 ETF。輸入 「查看我的投資組合」 進一步了解損益。"
    except:
        return ""

def install_packages(packages: list[str]) -> bool:
    """Install missing packages using pip."""
    import subprocess
    import sys
    
    print(f"\n正在嘗試安裝缺失套件：{', '.join(packages)}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("[OK] 套件安裝成功！")
        return True
    except Exception as e:
        print(f"[錯誤] 套件安裝失敗：{e}")
        return False


def cmd_check_env(install_deps: bool = False) -> int:
    """Check environment and dependencies."""
    print("ETF_TW 環境點檢中...")
    print("-" * 40)
    
    # 1. Python Environment Check
    import sys
    in_venv = sys.prefix != sys.base_prefix
    venv_status = "[OK] 處於虛擬環境中" if in_venv else "[警告] 未偵測到虛擬環境 (建議使用 venv 隔離)"
    
    print(f"[OK] Python 版本: {sys.version.split()[0]}")
    print(f"{venv_status}")
    
    # 2. Dependency Check
    missing = []
    # yfinance: data source, pandas/numpy: processing, shioaji: broker api
    for pkg in ["yfinance", "pandas", "numpy", "shioaji"]:
        try:
            __import__(pkg)
            print(f"[OK] 依賴套件: {pkg} 已安裝")
        except ImportError:
            missing.append(pkg)
            print(f"[錯誤] 依賴套件: {pkg} 未安裝")
    
    if missing:
        if install_deps:
            if install_packages(missing):
                missing = [] # Installed successfully
            else:
                return 1
        else:
            print("\n請執行: pip install " + " ".join(missing) + " 或使用 --install-deps 自動安裝")
            return 1
    
    # Check data files
    for name, path in [("ETF 資料", ETF_CURATED_PATH), ("券商資料", BROKER_PATH), 
                       ("帳本資料", LEDGER_PATH), ("資料來源健康矩陣", ROOT / "references" / "source_health_matrix.md")]:
        if path.exists():
            print(f"[OK] 資料檔案: {name} 存在")
        else:
            print(f"[錯誤] 資料檔案: {name} 缺失")
    
    # Check Source Health Summary
    matrix_path = ROOT / "references" / "source_health_matrix.md"
    if matrix_path.exists():
        print("\n資料來源健康度摘要：")
        content = matrix_path.read_text(encoding="utf-8")
        # Extract rows with score <= 3
        poor_sources = re.findall(r"\| (.*?) \|.*?\|.*?\| ([1-3]) \|", content)
        if poor_sources:
            for domain, score in poor_sources:
                print(f"  [警告] {domain.strip()}: 分數 {score} (建議改用其他來源)")
        else:
            print("  [OK] 所有來源運作異常風險低")

    print("\n環境檢查通過！")
    return 0


def cmd_update_matrix() -> int:
    """Update the source health matrix check date."""
    try:
        try:
            from scripts.update_source_matrix import update_checked_date
        except ImportError:
            import update_source_matrix
            update_checked_date = update_source_matrix.update_checked_date
            
        update_checked_date()
        return 0
    except Exception as e:
        print(f"[錯誤] 更新矩陣失敗: {e}")
        return 1


def cmd_init_env(install_deps: bool = False) -> int:
    """Initialize configuration and data files."""
    # Run check first to handle dependencies
    print("正在初始化 ETF_TW 環境...")
    if cmd_check_env(install_deps) != 0:
        return 1
    
    config_path = ROOT / "assets" / "config.json"
    example_path = ROOT / "assets" / "config.example.json"
    
    if not config_path.exists():
        if example_path.exists():
            import shutil
            shutil.copy(example_path, config_path)
            print(f"[OK] 已從範本建立設定檔: {config_path}")
        else:
            # Create a very basic config if example is missing
            basic_config = {
                "trading": {"default_mode": "paper"},
                "risk_controls": {"max_single_etf_percent": 60}
            }
            config_path.write_text(json.dumps(basic_config, indent=2), encoding="utf-8")
            print(f"[OK] 已建立基礎設定檔: {config_path}")
    else:
        print(f"! 設定檔已存在，跳過建立: {config_path}")
    
    # Create ledger if missing
    if not LEDGER_PATH.exists():
        LEDGER_PATH.write_text(json.dumps({"version": "1.0", "entries": []}, indent=2), encoding="utf-8")
        print(f"[OK] 已建立空帳本: {LEDGER_PATH}")
        
    print("\n初始化完成！")
    return 0

def format_mode_status(payload: dict) -> str:
    mode = str(payload.get("effective_mode") or "unknown").upper()
    account = payload.get("default_account") or "unknown"
    source = payload.get("data_source") or "unknown"
    health = "OK" if payload.get("health_check_ok") else "FAIL"
    return f"目前模式: {mode}\n預設帳戶: {account}\n資料來源: {source}\nhealth check: {health}"


def _run_live_health_check(account_alias: str | None = None) -> tuple[bool, str]:
    try:
        manager = get_account_manager()
        account = manager.get_account(account_alias)
        adapter = manager.get_adapter(account_alias)
        ok = asyncio.run(adapter.authenticate())
        if not ok:
            return False, "auth failed"
        asyncio.run(adapter.get_account_balance(account.get("account_id")))
        asyncio.run(adapter.get_positions(account.get("account_id")))
        return True, "OK"
    except Exception as e:
        return False, str(e)


def _get_default_broker(config: dict) -> str:
    """Resolve default broker from config, falling back to account alias prefix."""
    broker = config.get("trading", {}).get("default_broker")
    if broker:
        return broker
    # Fallback: strip trailing _01/_02 suffix from default_account alias
    account = config.get("default_account", "")
    if "_" in account:
        return account.rsplit("_", 1)[0]
    return account or "sinopac"


def cmd_mode(args: argparse.Namespace) -> int:
    manager = get_account_manager()
    config = manager.get_config()
    current = read_trading_mode_state()
    previous_mode = current.get("effective_mode") or "paper"
    manual_override = current.get("manual_override")

    if args.mode_action == "status":
        if not current:
            ok, msg = _run_live_health_check(config.get("default_account")) if config.get("default_account") else (False, "no default account")
            payload = resolve_effective_mode(config=config, manual_override=None, live_check_ok=ok, previous_mode="paper")
            payload.update({
                "default_account": config.get("default_account"),
                "default_broker": _get_default_broker(config),
                "health_check_message": msg,
            })
            current = write_trading_mode_state(None, payload)
        print(format_mode_status(current))
        return 0

    if args.mode_action == "paper":
        payload = resolve_effective_mode(config=config, manual_override="paper", live_check_ok=False, previous_mode=previous_mode)
        payload.update({
            "default_account": config.get("default_account"),
            "default_broker": _get_default_broker(config),
            "health_check_message": "manual paper switch",
        })
        write_trading_mode_state(None, payload)
        print(format_mode_status(payload))
        return 0

    ok, msg = _run_live_health_check(config.get("default_account"))
    payload = resolve_effective_mode(config=config, manual_override="live", live_check_ok=ok, previous_mode=previous_mode)
    payload.update({
        "default_account": config.get("default_account"),
        "default_broker": _get_default_broker(config),
        "health_check_message": msg,
    })
    write_trading_mode_state(None, payload)
    print(format_mode_status(payload))
    return 0 if payload.get("effective_mode") == "live-ready" else 1


def cmd_switch_account(args: argparse.Namespace) -> int:
    """Switch the default account."""
    manager = get_account_manager()
    if manager.set_default_account(args.alias):
        print(f"✓ 成功切換預設帳戶為：{args.alias}")
        return 0
    else:
        print(f"✗ 切換失敗：找不到帳戶別名 '{args.alias}'")
        return 1


def cmd_welcome() -> int:
    """Display welcome message with natural language examples."""
    summary = get_mini_summary()
    if summary:
        print(f"\n{summary}\n")
    
    print("👋 歡迎使用 ETF_TW 台灣 ETF 投資助理！")
    print("=" * 66)
    print("您可以嘗試對我說以下指令（口語表達即可）：")
    
    if summary:
        print("\n📈 常用回報 (針對老手)")
        print("  • 「查看我的投資組合與損益」 (portfolio)")
        print("  • 「我目前還有多少現金？」")
        print("  • 「賣掉所有的 0050」")
    
    print("\n🐣 新手入門 (按讚必讀！)")
    print("  • 「列出所有支援的 ETF」")
    print("  • 「幫我找看看有沒有 0050 的資料」")
    print("  • 「有哪些大盤型的 ETF？」")
    print("\n📊 分析類")
    print("  • 「比較 0050 和 006208 哪一檔費用比較低？」")
    print("  • 「如果我每個月存 1 萬元到 0050，10 年後大約有多少錢？」")
    print("\n💹 交易與風控 (模擬)")
    print("  • 「驗證下單：買入 100 股 0050，價格 185 元」")
    print("  • 「預覽買進 0050 10 張的成本與風險」")
    print("  • 「正式執行模擬交易：買入 0050 十股」")
    print("\n💼 帳戶管理")
    print("  • 「幫我列出目前所有的模擬帳戶」")
    print("  • 「查看元大證券的支援現況」")
    print("\n🔧 系統點檢")
    print("  • 「檢查目前的環境依賴是否正確」 (check)")
    print("  • 「初始化我的投資工作區」 (init)")
    print("=" * 60)
    print("💡 提示：所有操作目前預設在【模擬 (Paper)】模式下執行，確保您的資產安全。")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Start the dashboard web server."""
    try:
        import uvicorn
    except ImportError:
        print("錯誤：未安裝 uvicorn，請執行 pip install uvicorn")
        return 1

    port = args.port or 5055
    host = args.host or "127.0.0.1"
    print(f"啟動 ETF_TW Dashboard 於 http://{host}:{port}")

    # Ensure dashboard is importable
    dashboard_path = ROOT / "dashboard"
    if str(dashboard_path) not in sys.path:
        sys.path.append(str(dashboard_path))

    uvicorn.run("app:app", host=host, port=port, reload=args.reload)
    return 0


# ==================== CLI Builder ====================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="etf-tw", description="ETF_TW 台灣 ETF 投資助理 - 多券商支援版")
    sub = parser.add_subparsers(dest="command", required=True, help="子指令")
    
    # Onboarding
    sub.add_parser("welcome", help="顯示歡迎訊息與使用範例")
    sub.add_parser("list", help="列出精選 ETF 清單")
    
    # Dashboard
    p_dash = sub.add_parser("dashboard", help="啟動 ETF_TW 決策儀表板 (Web UI)")
    p_dash.add_argument("--host", default="127.0.0.1", help="監聽地址 (預設 127.0.0.1)")
    p_dash.add_argument("--port", type=int, default=5055, help="監聽連接埠 (預設 5055)")
    p_dash.add_argument("--reload", action="store_true", help="啟用熱重載 (開發模式)")

    p_search = sub.add_parser("search", help="搜尋 ETF (支援代碼、名稱與摘要)")
    p_search.add_argument("keyword", help="關鍵字")
    
    p_category = sub.add_parser("category", help="依類別篩選 ETF")
    p_category.add_argument("category", help="類別名稱 (如：高股息、大盤型)")
    
    p_compare = sub.add_parser("compare", help="比較兩檔 ETF 的成本、風險與特性")
    p_compare.add_argument("symbol1", help="第一檔 ETF 代碼")
    p_compare.add_argument("symbol2", help="第二檔 ETF 代碼")
    
    p_calc = sub.add_parser("calc", help="定期定額 (DCA) 投資複利試算")
    p_calc.add_argument("symbol", help="ETF 代碼")
    p_calc.add_argument("amount", type=float, help="每月投入金額")
    p_calc.add_argument("years", type=int, help="投資年數")
    p_calc.add_argument("--annual-return", type=float, default=0.06, help="假設年化報酬率 (預設 0.06)")
    
    p_guide = sub.add_parser("guide", help="投資新手導引 (開戶、手續費、稅務)")
    p_guide.add_argument("topic", help="主題 (account/discount/docs/tax)")
    
    p_beginner = sub.add_parser("beginner", help="新手基礎知識庫")
    p_beginner.add_argument("topic", help="主題 (basics/choose-style/first-trade/pitfalls/risk)")
    
    p_preview = sub.add_parser("preview-order", help="下單預演 (計算成本與驗證風控)")
    p_preview.add_argument("file", nargs="?", help="委託指令檔 (JSON)")
    
    p_validate = sub.add_parser("validate-order", help="驗證下單指令合法性")
    p_validate.add_argument("file", nargs="?", help="委託指令檔 (JSON)")
    
    # Paper trade
    p_paper = sub.add_parser("paper-trade", help="執行模擬交易 (Paper Trade)")
    p_paper.add_argument("--file", help="委託指令檔 (JSON)")
    p_paper.add_argument("--symbol", help="ETF 代碼")
    p_paper.add_argument("--side", choices=["buy", "sell"], help="買進或賣出")
    p_paper.add_argument("--quantity", type=int, help="數量 (股)")
    p_paper.add_argument("--price", type=float, help="限價價格")
    
    # Portfolio
    sub.add_parser("portfolio", help="查看當前模擬投資組合狀態與損益")
    
    # Orders and trades
    p_orders = sub.add_parser("orders", help="查看當前帳戶的委託清單")
    p_orders.add_argument("--account", "-a", help="帳戶別名 (預設使用 default)")

    p_trades = sub.add_parser("list-trades", help="查看當前帳戶的成交歷史")
    p_trades.add_argument("--account", "-a", help="帳戶別名 (預設使用 default)")

    # Account switching
    p_switch = sub.add_parser("switch-account", help="切換預設帳戶")
    p_switch.add_argument("alias", help="欲切換的帳戶別名")

    p_mode = sub.add_parser("mode", help="交易模式狀態查詢與切換 (paper/live)")
    p_mode.add_argument("mode_action", choices=["status", "paper", "live"], help="動作：status(查看), paper(切換為模擬), live(切換為實盤)")
    
    # New account management commands (Phase 4)
    p_accounts = sub.add_parser("accounts", help="列出所有已配置的帳戶")
    
    p_brokers = sub.add_parser("brokers", help="列出支援的券商列表")
    
    p_health = sub.add_parser("health", help="執行券商/帳戶連線健康檢查")
    p_health.add_argument("--account", "-a", help="帳戶別名")
    
    p_preview_acc = sub.add_parser("preview-account", help="依指定帳戶執行下單預演")
    p_preview_acc.add_argument("file", nargs="?", help="委託指令檔 (JSON)")
    p_preview_acc.add_argument("--account", "-a", help="帳戶別名")
    
    p_validate_acc = sub.add_parser("validate-account", help="依指定帳戶驗證下單指令")
    p_validate_acc.add_argument("file", nargs="?", help="委託指令檔 (JSON)")
    p_validate_acc.add_argument("--account", "-a", help="帳戶別名")
    
    p_paper_acc = sub.add_parser("paper-account", help="依指定帳戶執行模擬交易")
    p_paper_acc.add_argument("file", nargs="?", help="委託指令檔 (JSON)")
    p_paper_acc.add_argument("--account", "-a", help="帳戶別名")

    p_submit_preview = sub.add_parser("submit-preview", help="實盤下單前的最終確認清單")
    p_submit_preview.add_argument("file", nargs="?", help="委託指令檔 (JSON)")
    p_submit_preview.add_argument("--account", "-a", help="帳戶別名")

    # Tradable universe (TWSE + TPEx)
    sub.add_parser("universe-sync", help="同步台灣全市場 ETF 代碼表 (上市、上櫃)")

    p_universe_list = sub.add_parser("universe-list", help="列出全市場 ETF 代碼")
    p_universe_list.add_argument("--exchange", choices=["TWSE", "TPEx"], help="篩選交易所：TWSE(上市), TPEx(上櫃)")
    p_universe_list.add_argument("--limit", type=int, default=50, help="顯示上限 (預設 50)")

    p_universe_search = sub.add_parser("universe-search", help="在全市場中搜尋 ETF")
    p_universe_search.add_argument("query", help="搜尋關鍵字")
    p_universe_search.add_argument("--limit", type=int, default=50, help="顯示上限 (預設 50)")

    p_universe_show = sub.add_parser("universe-show", help="顯示單一 ETF 的詳細資料 (包含精選中繼資料)")
    p_universe_show.add_argument("symbol", help="ETF 代碼")

    # Helper commands
    p_check = sub.add_parser("check", help="檢查執行環境與套件依賴")
    p_check.add_argument("--install-deps", action="store_true", help="自動安裝缺失的依賴套件")
    
    p_init = sub.add_parser("init", help="初始化設定檔與資料夾結構")
    p_init.add_argument("--install-deps", action="store_true", help="初始化時同步安裝依賴套件")
    
    sub.add_parser("update-matrix", help="更新資料來源健康矩陣檢核時間")
    
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    
    # Onboarding
    if args.command == "welcome":
        return cmd_welcome()
    
    # Original commands
    if args.command == "list":
        return cmd_list(args)
    if args.command == "dashboard":
        return cmd_dashboard(args)
    if args.command == "search":
        return cmd_search(args)
    if args.command == "category":
        return cmd_category(args)
    if args.command == "compare":
        return cmd_compare(args)
    if args.command == "calc":
        return cmd_calc(args)
    if args.command == "guide":
        return cmd_guide(args)
    if args.command == "beginner":
        return cmd_beginner(args)
    if args.command == "preview-order":
        return cmd_preview_order(args)
    if args.command == "validate-order":
        return cmd_validate_order(args)
    if args.command == "paper-trade":
        return cmd_paper_trade(args)
    if args.command == "portfolio":
        return cmd_portfolio(args)
    if args.command == "orders":
        return asyncio.run(cmd_orders(args))
    if args.command == "list-trades":
        return asyncio.run(cmd_list_trades(args))
    if args.command == "switch-account":
        return cmd_switch_account(args)
    if args.command == "mode":
        return cmd_mode(args)
    
    # New account management commands (Phase 4)
    if args.command == "accounts":
        return cmd_list_accounts(args)
    if args.command == "brokers":
        return cmd_list_brokers(args)
    if args.command == "health":
        return asyncio.run(cmd_broker_health(args))
    if args.command == "preview-account":
        return asyncio.run(cmd_preview_account(args))
    if args.command == "validate-account":
        return asyncio.run(cmd_validate_account(args))
    if args.command == "paper-account":
        return asyncio.run(cmd_paper_account(args))
    if args.command == "submit-preview":
        return asyncio.run(cmd_submit_preview(args))

    # Tradable universe commands
    if args.command == "universe-sync":
        return cmd_universe_sync()
    if args.command == "universe-list":
        return cmd_universe_list(args)
    if args.command == "universe-search":
        return cmd_universe_search(args)
    if args.command == "universe-show":
        return cmd_universe_show(args)
    
    if args.command == "check":
        return cmd_check_env(args.install_deps)
    
    if args.command == "init":
        return cmd_init_env(args.install_deps)
    
    if args.command == "update-matrix":
        return cmd_update_matrix()
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
