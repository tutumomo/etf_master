import shioaji as sj
import json
import os
from pathlib import Path

# Load config
CONFIG_PATH = Path("~/.hermes/profiles/etf_master/skills/ETF_TW/assets/config.json").expanduser()
with open(CONFIG_PATH) as f:
    config_data = json.load(f)
    config = config_data["brokers"]["sinopac"]

api = sj.Shioaji(simulation=True)
api.login(api_key=config["api_key"], secret_key=config["secret_key"])

# Index probe
print("--- Index Stats ---")
contracts = []
try:
    # 1. TAIEX
    taiex = api.Contracts.Indexs.TSE["001"]
    contracts.append(taiex)
    print(f"TAIEX: {taiex}")
    
    # 2. VIX
    vix = api.Contracts.Indexs.TSE.get("03064")
    if vix:
        contracts.append(vix)
        print(f"VIX: {vix}")
    else:
        print("VIX (03064) not found in Indexs.TSE")
except Exception as e:
    print(f"Index query error: {e}")

if contracts:
    print("\n--- Snapshots ---")
    snaps = api.snapshots(contracts)
    for s in snaps:
        print(f"Symbol: {s.code}, Price: {s.close}, Change: {s.change_rate*100:.2f}%")

api.logout()
