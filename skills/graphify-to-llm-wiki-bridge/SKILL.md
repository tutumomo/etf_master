---
name: graphify-to-llm-wiki-bridge
description: 將 graphify 知識圖譜輸出對應寫入 llm-wiki 頁面的流程。用於整合 Graphify 探勘結果與既有 wiki 知識庫。
category: knowledge-workflow
created: 2026-04-14
updated: 2026-04-14
tags: [graphify, llm-wiki, 知識管理, 圖譜]
sources: []
---

# Graphify → LLM Wiki 橋接流程

將 graphify 圖譜輸出（有節點/邊/超邊的 `graph.json`）對應寫入 wiki 頁面的標準流程。

## 觸發條件

當 graphify 對某代碼庫完成提取並生成 `graph.json` 後，需要將結果同步到 wiki。

## 流程步驟

### Step 1：確認 wiki 目錄結構

Wiki 頁面分三層，**不在根目錄**：
```
wiki/
  entities/    ← ETF/工具實體頁（如 00679B-yuanta-us-20y-bond.md）
  concepts/    ← 概念頁（如 decision-chain.md, 知識圖譜-vs-RAG.md）
  comparisons/ ← 比較頁（如 0050-vs-006208.md）
  SCHEMA.md    ← frontmatter 格式定義
  index.md     ← 頁面目錄
```

**用 `find` 而非 `ls` 確認路徑**，因為有些檔名含中文。

### Step 2：分析 graph.json 的可用數據

```python
import json
from pathlib import Path
from collections import defaultdict

gdata = json.loads(Path('graphify-out/graph.json').read_text())
nodes = gdata['nodes']       # 節點列表
links = gdata['links']       # 邊列表
hyperedges = gdata.get('hyperedges', [])  # 超邊（多實體關聯）

# 重要：graphify 的「ETF 節點」通常只有文件提及，資訊密度低
# 真正有價值的是 hyperedges（跨文件主題群）
```

### Step 3：根據目標選擇對應數據

| Wiki 頁類型 | Graphify 數據源 | 寫入內容 |
|------------|----------------|----------|
| decision-chain 等概念頁 | `communities`, `god_nodes` | 系統架構、God Nodes、社群對照 |
| ETF entity 頁 | `hyperedges` | ETF 共現關聯（來源文件維度） |
| 知識圖譜-vs-RAG 頁 | graph.json 統計 | 實測數據（節點數、覆蓋率、Token消耗） |
| graphify entity 頁 | GRAPH_REPORT.md | 完整實測結果 |

### Step 4：ETF 共現寫入（最常見的對應任務）

```python
# Step A：建立 ticker → wiki filename 對照
ETF_MAP = {
    '00679B': '00679B-yuanta-us-20y-bond',
    '00878':  '00878-cathay-esg-high-dividend',
    # ... 只對已存在 wiki 實體頁的 ticker 建立對照
}

# Step B：從 hyperedges 建立共現矩陣
etf_cooccur = defaultdict(lambda: defaultdict(set))
for h in hyperedges:
    nodes = h.get('nodes', [])
    source = Path(h.get('source_file', '')).name
    for node in nodes:
        ticker = node.replace('etf_', '').upper()
        if ticker in ETF_MAP:
            for other in nodes:
                other_ticker = other.replace('etf_', '').upper()
                if other_ticker != ticker and other_ticker in ETF_MAP:
                    etf_cooccur[ticker][other_ticker].add(source)

# Step C：寫入每個 ETF entity 頁
for ticker, wiki_file in ETF_MAP.items():
    if not wiki_file: continue
    wiki_path = Path(f'wiki/entities/{wiki_file}.md')
    if not wiki_path.exists(): continue
    
    # 在 ## 關聯 ETF 或 ## 備註 前插入 ## 系統共現關聯（Graphify 探勘）
    crossref = build_crossref_section(ticker, etf_cooccur.get(ticker, {}))
    # ...
```

### Step 5：更新 frontmatter 和 log

每個變更都要：
1. 更新 `updated: YYYY-MM-DD` frontmatter
2. 追加到 `wiki/log.md`

## 重要發現（經驗教訓）

### graphify ETF 節點的真相
- graphify 的 `etf_xxxxx` 節點**只是文件提及**，資訊密度低
- 真正有價值的是 **hyperedges**（跨文件主題群， ETF 生態佔 8 個）
- 代碼邏輯關聯極少（只有 `live_trading_sop_code_1` 提及 TSE00878）

### Wiki 路徑陷阱
- `read_file` 和 `write_file` 工具**不支援自動路徑擴展**
- 直接用 `wiki/decision-chain.md` 會失敗（N/A）
- 必須用完整路徑：`wiki/concepts/decision-chain.md`

### Frontmatter 格式
```yaml
---
title: 頁面標題
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [標籤1, 標籤2]
sources: [raw/來源檔案]
---
```
- 所有日期用 ISO 格式（YYYY-MM-DD）
- 更新時只改 `updated` 欄位

## 驗證步驟

```bash
# 確認目標頁面存在且有正確的共現內容
grep -A 15 "系統共現關聯" wiki/entities/00679B-yuanta-us-20y-bond.md

# 確認 frontmatter 日期已更新
grep "updated:" wiki/entities/*.md

# 確認 log 已追加
tail -20 wiki/log.md
```

## 已知限制

- ETF 節點是「文件提及」維度，非「投資邏輯關聯」維度
- 尚未建立 wiki 實體頁的 ticker（如 00637L、00892、00922、00923）無法直接對應
- graphify 的 confidence=INFERRED 需人工審核再寫入 wiki
