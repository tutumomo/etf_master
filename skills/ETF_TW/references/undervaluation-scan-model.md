---
name: etf-tw-undervaluation-scan
version: 1.0.0
description: >
  台灣 ETF 低估排行掃描 — 6 因子評分模型，結合 yfinance 估值/技術指標 + 宏觀情境，
  產出 TOP 10 低估 ETF 排行榜與主題歸納。
---

# 台灣 ETF 低估排行掃描 (Undervaluation Scan)

## 適用場景
- 使用者問「最被低估的 ETF」「哪些 ETF 有價值」「現在什麼值得買」
- 定期（月/季）檢視投資組合中是否有低估機會

## 執行步驟

### Step 1：取得 ETF 宇宙 + 市場情境
```bash
# 從 ETF_TW state 取得追蹤標的清單與報價
skills/ETF_TW/.venv/bin/python3 -c "
import json; from pathlib import Path
STATE = Path('skills/ETF_TW/instances/etf_master/state')
mc = json.loads((STATE / 'market_cache.json').read_text())
mctx = json.loads((STATE / 'market_context_taiwan.json').read_text())
ectx = json.loads((STATE / 'market_event_context.json').read_text())
# 輸出 quotes + regime
"
```

### Step 2：yfinance 批次拉取估值數據
- ** ticker 格式**：一般 ETF 用 `.TW`；代號尾碼 B（債券型）用 `.TWO`
  - ✅ `0050.TW`, `00919.TW`, `00878.TW`
  - ✅ `00679B.TWO`, `00687B.TWO`, `00720B.TWO`, `00694B.TWO`
- 關鍵欄位：`trailingPE`, `dividendYield`, `fiftyTwoWeekHigh/Low`, `navPrice`
- **陷阱**：`dividendYield` 有時回傳百分比（>1），需除以 100

### Step 3：yfinance 批次拉取技術指標
- 用 `history(period="6mo")` 自算 RSI(14)、MACD、SMA20/60、1M/3M 動能、波動率
- **陷阱**：0050/0056 的 RSI 計算偶爾因 `NoneType` 錯誤，需獨立 retry

### Step 4：web_search 補充宏觀情境
- 搜尋關鍵字：Fed 降息預期、美債 ETF 降息受惠、高股息 ETF 配息穩定度
- 用於宏觀順風因子評分 + 報告中的前提假設說明

### Step 5：6 因子評分 + 排行

| 因子 | 滿分 | 低估條件 | 資料來源 |
|------|------|----------|----------|
| PE 折價率（同類比較） | 25 | PE 低於同類均價；債券型用殖利率替代 | yfinance `trailingPE` |
| 殖利率溢價 | 20 | ≥10%=20, ≥7%=15, ≥5%=12, ≥3%=8, <3%=3 | yfinance `dividendYield` |
| RSI 位置 | 20 | <45=20, <55=17, <65=12, <72=7, ≥72=3 | yfinance history 自算 |
| 距 52 週高點 | 15 | >5%=15, >3%=10, >1%=5, ≤1%=2 | yfinance `fiftyTwoWeekHigh` |
| 價格 vs SMA60 | 10 | <-2%=10, <2%=8, <5%=5, <10%=3, ≥10%=1 | yfinance history 自算 |
| 宏觀順風 | 10 | 債券型=9, 高股息=6, 市值型=3, 科技=2 | web_search + 判斷 |

### Step 6：輸出報告
1. **排行榜表格**（代號、名稱、低估邏輯、價格、殖利率、RSI、距高點、風險）
2. **三大低估主題**歸納（例如：美債反轉機會、低PE高股息、中短債避險）
3. **誠實聲明**（前提假設、數據時效、殖利率是否含資本利得分配）

## ETF 分類基準（PE 同類比較用）

| 分類 | 代表代號 | PE 均值參考 |
|------|----------|-----------|
| 市值型 | 0050, 006208, 00922, 00923 | ~29.2 |
| 高股息 | 0056, 00713, 00878, 00919, 00929, 00939, 00940 | ~16.0 |
| 高股息/ESG | 00830 | ~49 |
| 科技/主題 | 00892, 00935 | ~42 |
| 債券型 | 00679B, 00687B, 00694B, 00720B | N/A（用殖利率替代） |

## 債券型特殊處理
- 無 PE → 殖利率 >4% 給基礎分 15
- 宏觀順風 9/10（降息 + 地緣避險雙重受惠）
- 存續期間愈長 → Fed 降息時價格彈性愈大（00679B/00687B ≈ 16 年）
- 00720B（7-10 年）殖利率反而比長債高 → 因長債溢價壓縮利差

## 實踐捷徑（2026-04-26 實測沉澱）

### 最佳化流程：跳過 Step 3 的 yfinance 技術指標自算
- **不需要**用 `history(period="6mo")` 自算 RSI/MACD/SMA60
- `market_intelligence.json`（來自 `sync_ohlcv_history.py`）已包含 RSI、momentum_20d、sharpe_30d、return_1y
- 直接從 intelligence 讀取 RSI 和 momentum_20d（替代 SMA60），節省 80% 的 API 呼叫與計算時間
- 實測：18 檔 ETF 從 ~3 分鐘 → ~8 秒（僅 yfinance .info 批次拉 PE/殖利率/52W 高低）

### 資料來源優先序（實測修正）
- **Step 1 實際操作**：讀 `watchlist.json` → 取 `items[].symbol`（非 `symbols` 頂層陣列）
- **RSI / momentum / sharpe**：優先從 `market_intelligence.json` 的 `intelligence` dict 取（非 yfinance 自算）
- **PE / 殖利率 / 52W 高低**：從 yfinance `.info` 批次拉（唯一需要 yfinance 的環節）
- **market_cache.json**：報價用，但 price=None 時改用 intelligence 的 `last_price`
- **market_context_taiwan.json**：部分欄位可能為 N/A（未觸發 generate），fallback 用 intelligence 推算

### Step 5 評分實作要點
- PE 折價率公式：`15 + (PE_ref - PE) / PE_ref * 50`，cap 在 0~25
- 債券型 PE=None → PE折價固定給 15
- SMA60 維度改用 momentum_20d 替代：<-2%=10, <2%=8, <5%=5, <10%=3, ≥10%=1
- 分類 PE 均值需定期重新校準（目前：市值~29.2, 高股息~16.0, 科技~42, ESG~49）

### 報告輸出發現
- 極端過熱信號（全市值型+科技 RSI 76~82）時，TOP 10 會完全被債券+高股息佔據
- 這是正常現象：低估模型在牛市頂部自然偏防禦
- 需在報告中明確標記「過熱區間不建議追價」避免誤導

## 陷阱與教訓

### yfinance 常見失敗
- `analyze_stock.py --fast`：大量 404 錯誤，台灣 ETF 不適用
- `dividends.py`：對台灣 ETF 回傳「does not pay a dividend」（誤判），不可靠
- `.info` 端點偶發 ConnectionError（curl:56），需 retry 或改用 `.history()` 推算
- `navPrice` 欄位經常回傳 None → 折溢價需改從 web_search 取得

### 正確 ticker 格式
- 尾碼 B 的債券 ETF → `.TWO`（如 00679B.TWO）
- 其餘 → `.TW`（如 0050.TW）
- `.TWO` 的 `info` 回傳欄位較少（無 PE/PB），需靠殖利率替代

### 殖利率拆解
- 高股息 ETF 殖利率 10%+ 可能含資本利得分配（非純收益），不可持續
- 需搜尋該 ETF 最新配息組成（收益分配 vs 資本利得 vs 收益平準金）
