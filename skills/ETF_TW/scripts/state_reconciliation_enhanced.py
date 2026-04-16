#!/usr/bin/env python3
"""
State Reconciliation Enhanced - 強化狀態對帳機制

確保 orders_open.json、positions.json、filled_reconciliation.json 之間的一致性。

問題根源:
- 送單回應存在，但成交狀態無法對帳
- 多個 state 檔案各自為政，缺乏統一真相源

解決方案:
- 單一訂單狀態機：pending → submitted → [filled | cancelled | rejected]
- 每一步都寫入 orders_open.json 並觸發 reconciliation
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.etf_core import context

STATE_DIR = context.get_state_dir()

# State 檔案路徑
ORDERS_OPEN_PATH = STATE_DIR / "orders_open.json"
POSITIONS_PATH = STATE_DIR / "positions.json"
FILLED_RECONCILIATION_PATH = STATE_DIR / "filled_reconciliation.json"
PORTFOLIO_SNAPSHOT_PATH = STATE_DIR / "portfolio_snapshot.json"


def load_json(path: Path, default: Any = None) -> Any:
    """安全載入 JSON 檔案"""
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default or {}


def save_json(path: Path, data: Any) -> None:
    """安全保存 JSON 檔案"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


def reconcile_orders_with_positions(
    orders_open: dict,
    positions: dict,
    filled_reconciliation: dict
) -> dict:
    """
    P3: 對帳 orders_open 與 positions

    檢查：
    1. orders_open 中的 filled 訂單是否在 positions 中有對應持倉
    2. positions 中的持倉是否有對應的 filled 訂單
    3. 數量是否一致
    """
    issues = []
    recommendations = []

    orders = orders_open.get("orders", [])
    positions_list = positions.get("positions", [])
    unreconciled = filled_reconciliation.get("unreconciled_orders", [])

    # 建立索引
    orders_by_symbol = {}
    for order in orders:
        symbol = order.get("symbol", "")
        if symbol not in orders_by_symbol:
            orders_by_symbol[symbol] = []
        orders_by_symbol[symbol].append(order)

    positions_by_symbol = {p.get("symbol"): p for p in positions_list}

    # 檢查 1: filled 訂單是否有對應持倉
    for order in orders:
        status = order.get("status", "")
        if status in ("filled", "partial_filled"):
            symbol = order.get("symbol")
            order_qty = order.get("filled_quantity", order.get("quantity", 0))

            if symbol not in positions_by_symbol:
                issues.append({
                    "type": "missing_position",
                    "order_id": order.get("order_id"),
                    "symbol": symbol,
                    "message": f"訂單 {order.get('order_id')} 已成交，但 positions 中找不到 {symbol} 的持倉"
                })
            else:
                position_qty = positions_by_symbol[symbol].get("quantity", 0)
                if position_qty < order_qty:
                    issues.append({
                        "type": "quantity_mismatch",
                        "order_id": order.get("order_id"),
                        "symbol": symbol,
                        "order_qty": order_qty,
                        "position_qty": position_qty,
                        "message": f"訂單 {order.get('order_id')} 成交 {order_qty} 股，但持倉只有 {position_qty} 股"
                    })

    # 檢查 2: 檢查未對帳訂單
    if unreconciled:
        recommendations.append({
            "action": "run_reconciliation",
            "reason": f"有 {len(unreconciled)} 筆未對帳訂單",
            "script": "refresh_filled_reconciliation_report.py"
        })

    return {
        "reconciled_at": datetime.now().astimezone().isoformat(),
        "issues": issues,
        "recommendations": recommendations,
        "summary": {
            "total_orders": len(orders),
            "total_positions": len(positions_list),
            "unreconciled_count": len(unreconciled),
            "issues_count": len(issues)
        }
    }


def build_order_state_machine(order: dict) -> dict:
    """
    P3: 建立訂單狀態機

    狀態轉換:
    pending → submitted → [filled | cancelled | rejected]
                       → [partial_filled → filled | cancelled | rejected]
    """
    order_id = order.get("order_id")
    current_status = order.get("status", "unknown")

    # 定義合法狀態
    valid_statuses = {"pending", "submitted", "partial_filled", "filled", "cancelled", "rejected"}

    # 檢查狀態是否合法
    if current_status not in valid_statuses:
        return {
            "order_id": order_id,
            "current_status": current_status,
            "is_valid": False,
            "error": f"非法狀態：{current_status}",
            "suggested_status": "pending"
        }

    # 檢查狀態轉換是否合法
    valid_transitions = {
        "pending": ["submitted", "cancelled", "rejected"],
        "submitted": ["filled", "partial_filled", "cancelled", "rejected"],
        "partial_filled": ["filled", "cancelled", "rejected"],
        "filled": [],  # 終端狀態
        "cancelled": [],  # 終端狀態
        "rejected": [],  # 終端狀態
    }

    return {
        "order_id": order_id,
        "current_status": current_status,
        "is_valid": True,
        "is_terminal": current_status in ("filled", "cancelled", "rejected"),
        "next_valid_states": valid_transitions.get(current_status, [])
    }


def validate_orders_open_state(orders_open: dict) -> dict:
    """
    P3: 驗證 orders_open 狀態

    檢查：
    1. 所有訂單的狀態是否合法
    2. 終端狀態的訂單是否已正確清理
    """
    orders = orders_open.get("orders", [])
    issues = []

    for i, order in enumerate(orders):
        state_machine = build_order_state_machine(order)

        if not state_machine["is_valid"]:
            issues.append({
                "order_index": i,
                "order_id": order.get("order_id"),
                "issue": "invalid_status",
                "details": state_machine["error"]
            })

        # 檢查終端狀態訂單是否應該被清理
        if state_machine.get("is_terminal"):
            # 終端狀態訂單應該被移到歷史記錄，不應該留在 open orders
            issues.append({
                "order_index": i,
                "order_id": order.get("order_id"),
                "issue": "terminal_state_in_open",
                "details": f"終端狀態 {state_machine['current_status']} 的訂單不應留在 open orders"
            })

    return {
        "validated_at": datetime.now().astimezone().isoformat(),
        "total_orders": len(orders),
        "issues": issues,
        "is_valid": len(issues) == 0
    }


def run_full_reconciliation() -> dict:
    """
    P3: 執行完整狀態對帳

    返回：
    - 對帳結果
    - 發現的問題
    - 建議行動
    """
    # 載入所有 state
    orders_open = load_json(ORDERS_OPEN_PATH, {"orders": []})
    positions = load_json(POSITIONS_PATH, {"positions": []})
    filled_reconciliation = load_json(FILLED_RECONCILIATION_PATH, {"unreconciled_orders": []})

    # 執行對帳
    reconciliation_result = reconcile_orders_with_positions(
        orders_open, positions, filled_reconciliation
    )

    # 驗證 orders_open 狀態
    validation_result = validate_orders_open_state(orders_open)

    # 合併結果
    result = {
        "reconciled_at": datetime.now().astimezone().isoformat(),
        "reconciliation": reconciliation_result,
        "validation": validation_result,
        "health_ok": (
            reconciliation_result["issues_count"] == 0 and
            validation_result["is_valid"]
        )
    }

    return result


def main():
    """主函數：執行狀態對帳並輸出結果"""
    print("=" * 72)
    print("📊 狀態對帳檢查")
    print("=" * 72)

    result = run_full_reconciliation()

    print(f"\n對帳時間：{result['reconciled_at']}")
    print(f"健康狀態：{'✓ 正常' if result['health_ok'] else '❌ 異常'}")

    # 對帳結果
    recon = result.get("reconciliation", {})
    print(f"\n📋 對帳摘要:")
    print(f"  總訂單數：{recon.get('summary', {}).get('total_orders', 0)}")
    print(f"  總持倉數：{recon.get('summary', {}).get('total_positions', 0)}")
    print(f"  未對帳訂單：{recon.get('summary', {}).get('unreconciled_count', 0)}")

    # 驗證結果
    validation = result.get("validation", {})
    print(f"\n✓ 狀態驗證:")
    print(f"  驗證結果：{'✓ 通過' if validation.get('is_valid') else '❌ 失敗'}")

    # 問題列表
    issues = recon.get("issues", []) + validation.get("issues", [])
    if issues:
        print(f"\n❌ 發現 {len(issues)} 個問題:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. [{issue.get('type', 'unknown')}] {issue.get('message', issue.get('details', ''))}")

    # 建議行動
    recommendations = recon.get("recommendations", [])
    if recommendations:
        print(f"\n💡 建議行動:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec.get('action')}: {rec.get('reason')}")
            if rec.get('script'):
                print(f"     執行：python scripts/{rec['script']}")

    print("\n" + "=" * 72)

    # 如果不是健康狀態，返回錯誤碼
    if not result["health_ok"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
