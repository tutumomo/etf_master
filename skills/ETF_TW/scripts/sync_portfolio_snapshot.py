import sys
import json
import re
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

# Multi-tenant Configuration
instance_id = context.get_instance_id()
STATE_DIR = context.get_state_dir()

# Memory and Snapshot paths (Instance-aware)
MEMORY_DIR = context.get_instance_dir() / "memory"
SNAPSHOT_PATH = STATE_DIR / "portfolio_snapshot.json"


def parse_currency_number(text: str) -> float:
    return float(text.replace(',', '').strip())


def build_snapshot_from_memory(memory_text: str) -> dict:
    holdings = []

    p_0050 = re.search(r'\*\*0050\*\*：持有 \*\*(\d+) 股\*\*，成本 \*\*(\d+(?:\.\d+)?)\*\*，現價 \*\*(\d+(?:\.\d+)?)\*\*', memory_text)
    p_00878 = re.search(r'\*\*00878\*\*：持有 \*\*(\d+) 股\*\*，成本 \*\*(\d+(?:\.\d+)?)\*\*，現價 \*\*(\d+(?:\.\d+)?)\*\*', memory_text)
    cash = re.search(r'\*\*帳戶餘額\*\*：([\d,]+) 元', memory_text)
    market_value = re.search(r'\*\*持倉總市值\*\*：([\d,]+) 元', memory_text)
    total_equity = re.search(r'\*\*帳面總資產\*\*：約 ([\d,]+) 元', memory_text)

    if p_0050:
        qty = int(p_0050.group(1))
        cost = float(p_0050.group(2))
        price = float(p_0050.group(3))
        holdings.append({
            'symbol': '0050',
            'quantity': qty,
            'average_cost': cost,
            'current_price': price,
            'market_value': round(qty * price, 2),
            'total_cost': round(qty * cost, 2),
        })

    if p_00878:
        qty = int(p_00878.group(1))
        cost = float(p_00878.group(2))
        price = float(p_00878.group(3))
        holdings.append({
            'symbol': '00878',
            'quantity': qty,
            'average_cost': cost,
            'current_price': price,
            'market_value': round(qty * price, 2),
            'total_cost': round(qty * cost, 2),
        })

    return {
        'holdings': holdings,
        'cash': parse_currency_number(cash.group(1)) if cash else 0,
        'market_value': parse_currency_number(market_value.group(1)) if market_value else round(sum(h['market_value'] for h in holdings), 2),
        'total_equity': parse_currency_number(total_equity.group(1)) if total_equity else 0,
        'updated_at': datetime.now().isoformat(),
        'source': 'etf_master_memory',
    }


from trading_mode import read_trading_mode_state


def build_snapshot_from_live_state_payloads(account_data: dict, positions_data: dict, updated_at: str | None = None) -> dict:
    # 載入現價快取以防 positions.json 缺少市值資訊
    cache_path = STATE_DIR / "market_cache.json"
    quotes = {}
    if cache_path.exists():
        try:
            quotes = json.loads(cache_path.read_text(encoding='utf-8')).get("quotes", {})
        except: pass

    holdings = []
    for p in positions_data.get("positions", []):
        symbol = p.get('symbol')
        qty = float(p.get('quantity', 0))
        # 優先從 cache 找現價，找不到才用 positions 裡的
        current_p = float(quotes.get(symbol, {}).get('current_price', 0) or p.get('current_price', 0))
        mkt_val = p.get('market_value')
        if mkt_val is None or mkt_val == 0:
            mkt_val = qty * current_p

        holdings.append({
            'symbol': symbol,
            'quantity': qty,
            'average_cost': p.get('average_price'),
            'current_price': current_p,
            'market_value': round(mkt_val, 2),
            'total_cost': round((p.get('average_price') or 0) * qty, 2),
            'unrealized_pnl': p.get('unrealized_pnl') or round(mkt_val - ((p.get('average_price') or 0) * qty), 2)
        })

    market_value = round(sum(h['market_value'] for h in holdings), 2)
    cash = float(account_data.get("cash", 0) or 0)

    return {
        'holdings': holdings,
        'cash': cash,
        'market_value': market_value,
        'total_equity': round(market_value + cash, 2),
        'updated_at': updated_at or datetime.now().isoformat(),
        'source': 'live_broker',
    }


def build_snapshot_from_live_state(state_dir: Path) -> dict:
    account_path = state_dir / "account_snapshot.json"
    positions_path = state_dir / "positions.json"

    if not account_path.exists() or not positions_path.exists():
        raise FileNotFoundError("Live state files not found")

    account_data = json.loads(account_path.read_text(encoding='utf-8'))
    positions_data = json.loads(positions_path.read_text(encoding='utf-8'))
    updated_at = datetime.now().isoformat()
    return build_snapshot_from_live_state_payloads(account_data, positions_data, updated_at)

def main() -> int:
    mode_state = read_trading_mode_state()
    is_live = mode_state.get("effective_mode") == "live-ready"
    
    try:
        if is_live:
            print("DEBUG: Synchronizing from LIVE BROKER data")
            payload = build_snapshot_from_live_state(STATE_DIR)
        else:
            memory_dir = MEMORY_DIR
            memory_dir.mkdir(parents=True, exist_ok=True)
            # Try to find the most recent memory file in the directory
            memory_files = list(memory_dir.glob("*.md"))
            if not memory_files:
                raise FileNotFoundError(f"No memory files found in {memory_dir}")
                
            latest_memory = max(memory_files, key=lambda p: p.stat().st_mtime)
            print(f"DEBUG: Reading memory from {latest_memory}")
            memory_text = latest_memory.read_text(encoding='utf-8')
            payload = build_snapshot_from_memory(memory_text)
    except Exception as e:
        print(f"WARNING: Sync Failed - {e}")
        # Build a safe default payload for a new agent
        payload = {
            'holdings': [],
            'cash': 0,
            'market_value': 0,
            'total_equity': 0,
            'updated_at': datetime.now().isoformat(),
            'source': 'cold_start_initialization',
        }
    
    SNAPSHOT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PORTFOLIO_SNAPSHOT_SYNC_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
