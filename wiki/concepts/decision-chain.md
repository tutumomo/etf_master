---
title: 知識→行動決策鏈
created: 2026-04-11
updated: 2026-04-11
type: concept
tags: [投資策略, 市場體制, 風險]
sources: [ETF_TW/instances/etf_master/state/strategy_link.json]
---

# 知識→行動決策鏈

> 這是智慧體從「知道」到「做到」的完整路徑。每個 cron 任務都必須遵循此鏈，確保產出不是空泛的資訊，而是可驅動投資行動的判斷。

## 決策鏈五步驟

```
感知 → 判讀 → 預判 → 建議 → 行動
 │       │       │       │       │
資料    體制    走勢    配置    下單
獲取    歸類    推估    建議    執行
```

### Step 1：感知（資料獲取）
- **來源**：market_cache.json、watchlist.json、yfinance 即時報價
- **產出**：原始數據快照（價格、量、外資買賣超、技術指標）
- **對應 cron**：盤前準備、盤中掃描

### Step 2：判讀（體制歸類）
- **依據**：[[risk-signal]] 訊號 + [[market-view]] 體制判定
- **產出**：更新 market-view.md 的「當前體制判定」與「驅動因子」
- **對應 cron**：盤中智慧掃描、盤後收工

### Step 3：預判（走勢推估）
- **方法**：體制 + 驅動因子 + 歷史模式 → 判斷短期（1-5日）走勢方向
- **產出**：市場情境 2-3 種（樂觀/中性/悲觀）及其機率評估
- **對應 cron**：盤後收工（日級）、每週深度復盤（週級）

### Step 4：建議（配置調整）
- **依據**：預判 × [[家族投資需求]] × 風控硬限制
- **產出**：具體 ETF 調整建議（買/賣/持有 + 理由）
- **對應 cron**：每週深度復盤

### Step 5：行動（下單執行）
- **前提**：主人明確授權（正式下單指令）
- **產出**：ETF_TW live submit + broker_order_id 驗證
- **對應**：非 cron，由主人觸發

## 各 cron 任務在決策鏈中的角色

| 任務 | 感知 | 判讀 | 預判 | 建議 |
|------|------|------|------|------|
| 早班準備 | ✅ | ✅ | — | — |
| 盤中智慧掃描 | ✅ | ✅ | — | — |
| 盤後收工 | ✅ | ✅ | ✅ | — |
| 每週深度復盤 | — | ✅ | ✅ | ✅ |

## 品質控制

- 每步產出必須寫入 wiki 或 state（不能只留在 cron 輸出中消失）
- 判讀結論必須更新 [[market-view]] 的「當前體制判定」
- 風險訊號必須更新 [[risk-signal]] 的核心訊號表
- 預判必須包含情境機率（不能只給一種可能）
- 建議必須對應到家族成員需求（不能只說「建議加碼」而不說誰適合）
---

## Graphify 實測：ETF_TW 系統決策架構（2026-04-14 實測）

> 以下內容由 graphify 從 ETF_TW 代碼庫自動提取，社群偵測發現的系統架構。

### 核心系統社群

| 社群 | 主題 | 節點數 | 核心構念 |
|------|------|--------|----------|
| Community 4 | AI 決策自動化 | 71 | `ai_decision_generate()`, `auto_trade_submit()`, `AIDecisionOutcomeRequest` |
| Community 6 | AI Decision Bridge | 35 | `ai_decision_bridge`，人類與 AI 決策介面 |
| Community 7 | 溯源反思機制 | 30 | `_append_jsonl()`, `record_reflection()`, `_determine_review_window()` |
| Community 9 | 決策執行引擎 | 23 | `decide_action()`, `build_ai_decision_request()` |

### 系統三層決策架構（Graphify 發現）

```
Community 4/9：AI 決策生成層
  ai_decision_generate() → decide_action()
  → 產出：預測、操作建議

Community 6：AI Decision Bridge（人機介面）
  → 原則1：Dashboard 不直接依賴 AI 在線 RPC
  → 原則2：AI 建議必須是 decision artifact，不是文字
  → 原則3：持倉/委託/成交真相必須與 AI 建議分層
  → 原則4：自主下單是最後階段，不是第一階段

Community 7：溯源反思層
  → 每次决策寫入 ai_decision_outcome.jsonl
  → 人工 review ledger 閉環
```

### God Nodes 與系統邊界（Graphify 實測）

Graphify 識別出 5 個最高連接度節點，代表 ETF_TW 系統的核心抽象：

| God Node | 連接數 | 角色 |
|----------|--------|------|
| `Order` | 90 | 貫穿系統的委託抽象（preview/paper/live） |
| `BaseAdapter` | 86 | 券商適配器基類，連接多個系統社區 |
| `Position` | 59 | 持倉真相源 |
| `AccountBalance` | 59 | 帳戶真相源 |
| `AccountManager` | 40 | 多券商帳戶管理器 |

### 隱藏連結發現（Surprising Connections）

Graphify 的社群偵測發現了非顯見連結：
- `AccountManager` → 使用 → `BaseAdapter`（帳戶管理與券商適配器的依賴關係）
- `build_submit_order_row()` → 連接 → Community 0/1/3（委託執行跨越多個系統社區）

### 與決策鏈的對應

| Graphify 系統層 | 對應決策鏈 Step |
|----------------|----------------|
| MarketDataProvider + 即時報價 | Step 1：感知 |
| decide_action() + market regime | Step 2-3：判讀 + 預判 |
| AI Decision Bridge | Step 4：建議（含人工把關） |
| execute_trade() + shioaji live | Step 5：行動 |

### 實驗數據

- 提取覆蓋率：**75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS**
- 代碼/文件/理由節點比例：**1224 code : 1170 doc : 260 rationale**
- 超邊（ETF 生態）：8 個主題群，涵蓋 00679B、00878、00929 等（⚠️ 為文件提及頻率，非客觀投資重要性）


## 關聯頁面

- [[market-view]] — 體制判讀結果
- [[risk-signal]] — 風險訊號儀表板
- [[家族投資需求]] — 配置建議的依據
- [[知識圖譜-vs-RAG]] — 知識圖譜與 RAG 的對比分析