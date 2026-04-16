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

print("--- Searching for VIX ---")
try:
    for code, contract in api.Contracts.Indexs.TSE.items():
        if "VIX" in contract.name or "波動" in contract.name:
            print(f"Index TSE: {contract}")
    
    for code, contract in api.Contracts.Indexs.OTC.items():
        if "VIX" in contract.name or "波動" in contract.name:
            print(f"Index OTC: {contract}")

except Exception as e:
    print(f"Query error: {e}")

# Try to find USD/TWD
print("\n--- Searching for USD/TWD ---")
try:
    # Check if there are FX or Other categories
    pass
except Exception as e:
    print(f"FX search error: {e}")

# Skip logout to avoid segfault
os._exit(0)
