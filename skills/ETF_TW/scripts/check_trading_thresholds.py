import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE_DIR = context.get_state_dir()
SNAPSHOT_PATH = STATE_DIR / "portfolio_snapshot.json"
CONFIG_PATH = ROOT / "assets" / "config.json"

def main():
    if not SNAPSHOT_PATH.exists():
        print("SNAPSHOT_NOT_FOUND")
        return 0
    
    if not CONFIG_PATH.exists():
        print("CONFIG_NOT_FOUND")
        return 0
    
    try:
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding='utf-8'))
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"ERROR_LOADING_FILES: {e}")
        return 0
    
    thresholds = config.get("trading_thresholds", {})
    if not thresholds:
        print("NO_THRESHOLDS_CONFIGURED")
        return 0
    
    cash_min = thresholds.get("cash_percentage_min", 0)
    symbol_max = thresholds.get("symbol_weight_max", 100)
    
    total_equity = snapshot.get("total_equity", 0)
    if total_equity <= 0:
        print("TOTAL_EQUITY_IS_ZERO")
        return 0
    
    suggestions = []
    
    # Check Cash Percentage
    cash = snapshot.get("cash", 0)
    cash_pct = (cash / total_equity) * 100
    if cash_pct < cash_min:
        suggestions.append({
            "type": "cash_low",
            "symbol": "CASH",
            "side": "SELL", # Suggest selling holdings to get cash
            "reason": f"現金佔比 ({cash_pct:.1f}%) 低於下限 ({cash_min}%)",
            "action": "建議減碼持倉以增加現金水位"
        })
    
    # Check Symbol Weight
    for h in snapshot.get("holdings", []):
        weight = (h.get("market_value", 0) / total_equity) * 100
        if weight > symbol_max:
            suggestions.append({
                "type": "weight_high",
                "symbol": h.get("symbol"),
                "side": "SELL",
                "reason": f"標的 {h.get('symbol')} 佔比 ({weight:.1f}%) 超過上限 ({symbol_max}%)",
                "action": "建議部分減碼以符合風險分散政策"
            })
            
    snapshot["trigger_suggestions"] = suggestions
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"THRESHOLD_CHECK_OK (Found {len(suggestions)} suggestions)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
