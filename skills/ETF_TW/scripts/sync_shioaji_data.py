import shioaji as sj
import json
import os
from pathlib import Path
from datetime import datetime

# Load config
CONFIG_PATH = Path("~/.hermes/profiles/etf_master/skills/ETF_TW/assets/config.json").expanduser()
with open(CONFIG_PATH) as f:
    config_data = json.load(f)
    config = config_data["brokers"]["sinopac"]

OUTPUT_PATH = Path("~/.hermes/profiles/etf_master/skills/ETF_TW/data/market_macro.json").expanduser()

api = sj.Shioaji(simulation=True)
api.login(api_key=config["api_key"], secret_key=config["secret_key"])

data = {
    "updated_at": datetime.now().isoformat(),
    "indices": {},
    "fx": {}
}

try:
    # 1. TAIEX
    taiex = api.Contracts.Indexs.TSE["001"]
    snaps = api.snapshots([taiex])
    if snaps:
        s = snaps[0]
        data["indices"]["TAIEX"] = {
            "price": float(s.close),
            "change": float(s.change_price),
            "change_pct": float(s.change_rate) * 100,
            "volume": int(s.total_volume)
        }
    
    # 2. Try to find a VIX-like contract if possible
    # (Leaving placeholder or using proxy logic)
    data["indices"]["VIX_PROXY"] = "Check Macro Indicators"

except Exception as e:
    print(f"Error in sync: {e}")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Market macro data synced to {OUTPUT_PATH}")
os._exit(0)
