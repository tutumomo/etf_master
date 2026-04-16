#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Paths
WIKI_ENTITIES_DIR = Path("docs/wiki/shioaji/entities")
UNIVERSE_PATH = Path("skills/ETF_TW/data/etf_universe_tw.json")

def sanitize_filename(name):
    return name.replace("/", "-").replace(" ", "-").replace("<br>", "-").replace("(", "").replace(")", "").lower()

def generate_wiki():
    if not UNIVERSE_PATH.exists():
        print(f"Error: {UNIVERSE_PATH} not found.")
        return

    with open(UNIVERSE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    etfs = data.get("etfs", {})
    WIKI_ENTITIES_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for symbol, info in etfs.items():
        # Handle complex symbols like 006205<br>00625K
        clean_symbol = symbol.split("<br>")[0].split("(")[0].strip()
        filename = f"{clean_symbol}.md"
        filepath = WIKI_ENTITIES_DIR / filename
        
        name = info.get("name", "").replace("<br>", " ")
        issuer = info.get("issuer", "未知發行商")
        index = info.get("index_name", "未知指數")
        listing_date = info.get("listing_date", "未知日期")
        exchange = info.get("exchange", "TWSE")

        # Skip if exists to avoid overwriting dynamic content later
        if filepath.exists():
            continue

        content = f"""---
title: {name} ({clean_symbol})
created: 2026-04-16
updated: 2026-04-16
type: entity
tags: [shioaji.contract, etf.baseline]
quality: primary
source_type: spec
domain: shioaji
---

# {name} ({clean_symbol})

## 基礎資訊
- **代號**: {clean_symbol}
- **名稱**: {name}
- **發行商**: {issuer}
- **追蹤指數**: {index}
- **上市日期**: {listing_date}
- **交易市場**: {exchange}

## 動態診斷
> 此區塊將由自動化掃描任務定期更新。

## 相關連結
- [[shioaji-api]]
- [[market-view]]
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        count += 1

    print(f"Successfully generated {count} baseline Wiki pages.")

if __name__ == "__main__":
    generate_wiki()
