#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
STATE_DIR = Path("skills/ETF_TW/instances/etf_master/state")
WIKI_ENTITIES_DIR = Path("docs/wiki/shioaji/entities")
INTEL_PATH = STATE_DIR / "stock_intelligence.json"

def distill():
    if not INTEL_PATH.exists():
        print("No intelligence data to distill.")
        return

    with open(INTEL_PATH, "r", encoding="utf-8") as f:
        intel = json.load(f)

    tickers = intel.get("tickers", {})
    last_update = intel.get("last_update", datetime.now().isoformat())

    for symbol, data in tickers.items():
        # Handle .TW / .TWO suffix
        clean_symbol = symbol.split(".")[0]
        filepath = WIKI_ENTITIES_DIR / f"{clean_symbol}.md"

        if not filepath.exists():
            print(f"Skipping {symbol}: Wiki page not found.")
            continue

        # Extract core info from data
        rec = data.get("recommendation", "N/A")
        conf = data.get("confidence", "N/A")
        points = "\n".join([f"- {p}" for p in data.get("supporting_points", [])])
        caveats = "\n".join([f"- {cav}" for cav in data.get("caveats", [])])
        
        # Format dynamic block
        dynamic_content = f"""
## 動態診斷
**最後更新**: {last_update}
**量化評等**: {rec} (信心度: {conf})

### 核心要點
{points}

### 風險提示
{caveats}
"""
        
        # Update file content
        content = filepath.read_text(encoding="utf-8")
        
        # Replace the section using regex
        new_content = re.sub(
            r"## 動態診斷\n.*?(?=## 相關連結|\Z)", 
            dynamic_content + "\n", 
            content, 
            flags=re.DOTALL
        )
        
        # Update the 'updated' field in frontmatter
        new_content = re.sub(
            r"updated: \d{4}-\d{2}-\d{2}", 
            f"updated: {datetime.now().strftime('%Y-%m-%d')}", 
            new_content
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated dynamic intelligence for {clean_symbol}")

if __name__ == "__main__":
    distill()
