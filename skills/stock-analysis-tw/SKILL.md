---
name: stock-analysis-tw
description: >-
  基於 Yahoo Finance 的台股與 ETF 深度量化分析工具。
  支援 8 維度評分系統 (EPS/基本面/分析師/趨勢/板塊/動能/市場脈絡)、
  熱點掃描 (Hot Scanner) 與 早期訊號偵測 (Rumor Scanner)。
  針對台灣 ETF 市場 (0050, 0056, 00878) 進行優化，適合診斷標的健康度。
version: 6.2.0
---

# 台股/ETF 量化診斷器 (Stock Analysis TW)

本技能將 `yfinance` 報價數據與 8 個不同的量化維度相結合，為台股或 ETF 提供 0-100 分的綜合健檢報告。

## 主要指令

### 1) 個股/ETF 綜合分析 (`analyze`)
```bash
# 基礎 8 維度診斷
uv run skills/stock-analysis-tw/scripts/analyze_stock.py 0050.TW

# 快速模式 (跳過新聞與內部人數據)
uv run skills/stock-analysis-tw/scripts/analyze_stock.py 2330.TW --fast

# 複數標對比
uv run skills/stock-analysis-tw/scripts/analyze_stock.py 0050.TW 006208.TW 0056.TW
```

### 2) 股利策略分析 (`dividends`)
分析殖利率、配息穩定度與安全分。
```bash
# 分析高股息 ETF
uv run skills/stock-analysis-tw/scripts/dividends.py 00878.TW
```

### 3) 每週/每日熱點掃描 (`hot`)
找出目前市場中最熱門的標的與異常波動。
```bash
python3 skills/stock-analysis-tw/scripts/hot_scanner.py --no-social
```

### 4) 早期訊號偵測 (`rumors`)
偵測併購、法說會、內部人買賣與異常買盤訊號。
```bash
python3 skills/stock-analysis-tw/scripts/rumor_scanner.py
```

## 8 維度分析架構 (Taiwan Specific)

| 維度 (Dimension) | 權重 | 說明 |
|-----------|--------|-------------|
| 盈餘驚喜 (Earnings) | 30% | 法說會 EPS 優於預期程度 |
| 基本面 (Fundamentals) | 20% | P/E, 殖利率, 營收成長 |
| 分析師情緒 (Sentiment) | 20% | 投顧評等與目標價區域 |
| 歷史紀錄 (Historical) | 10% | 過去除權息或法說後的反應 |
| 市場脈絡 (Context) | 10% | VIX, 台指期 (TX) 與 0050 趨勢 |
| 板塊強弱 (Sector) | 15% | 同類別 ETF (如高股息/半導體) 的相對強度 |
| 技術動能 (Momentum) | 15% | RSI, 均線位置, 52 週高低區間 |
| 籌碼面 (Sentiment) | 10% | 三大法人买賣超 (簡化版) |

## 風險門檻警告 (Red Flags)

- ⚠️ **法說會/財報前夕**：距離公布日 < 14 天時發出警告。
- ⚠️ **漲幅過激**：5 日內漲幅 > 10% 時提示過熱風險。
- ⚠️ **超買訊號**：RSI > 70 且接近一年高點。
- ⚠️ **地緣政治**：偵測到台灣、兩岸、中東等關鍵字風險。

## 使用建議
- 適合在**開盤前 (08:30)** 執行 `rumor_scanner.py` 以捕捉前一晚美股與 ADR 的影響。
- 適合在**盤中**針對關注標的執行 `analyze_stock.py` 進行即時診斷。

---
本技能由原 `stock-analysis` 套件在地化重構，修正了 TWD 計價邏輯與台股特有的漲跌幅限制感應。
