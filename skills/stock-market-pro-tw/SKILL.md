---
name: stock-market-pro-tw
description: >-
  基於 Yahoo Finance (yfinance) 的全功能台股中控台：
  支援即時報價、基本面診斷、ASCII 趨勢分析、以及高解析度多指標技術線圖 (RSI/MACD/BB/VWAP/ATR)。
  特別整合台灣新聞搜尋與大盤趨勢比對邏輯。
---

# 專業市場分析台 (Stock Market Pro TW)

**Stock Market Pro TW** 是一個快速且本地優先的市場研究工具包。
提供乾淨的價格+基本面數據，生成可供發布的高畫質 PNG 線圖，並具備指標面板。針對台灣市場進行了本地化調整。

## 主要功能與指令

### 1) 即時報價與漲跌幅
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py price 0050.TW
# 簡寫模式
uv run skills/stock-market-pro-tw/scripts/yf.py 2330.TW
```

### 2) 基本面診斷 (Fundamentals)
包含：市值、預測盈餘比 (Forward PE)、每股盈餘 (EPS)、股東權益報酬率 (ROE)。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py fundamentals 00878.TW
```

### 3) 終端機 ASCII 趨勢
適合在命令列快速查看 6 個月趨勢。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py history 006208.TW 6mo
```

### 4) 高畫質專業線圖 (Pro PNG) ⭐
```bash
# 預設 K 線圖
uv run skills/stock-market-pro-tw/scripts/yf.py pro 0050.TW 6mo line
```

#### 進階指標 (Indicators)
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py pro 2330.TW 1y --rsi --macd --bb --vwap
```

- `--rsi` : RSI(14)
- `--macd`: MACD(12,26,9)
- `--bb`  : 布林通道 (20,2)
- `--vwap`: 區間成交量加權平均
- `--atr` : 平均真實波幅 ATR(14)

### 5) 綜合診斷報告 (One-shot Report)
輸出文字摘要並生成一張帶有 **BB + RSI + MACD** 的專業分析圖表。

```bash
uv run skills/stock-market-pro-tw/scripts/yf.py report 0050.TW 3mo
```

## 網頁輔助附加功能 (Add-ons)

### A) 台灣股市新聞搜尋 (`news`)
使用 DuckDuckGo 進行台灣本地新聞掃描。
```bash
uv run skills/stock-market-pro-tw/scripts/news.py 2330.TW --max 8
```

### B) 大盤趨勢比對
自動計算標的與台灣加權指數 (^TWII) 的相關性與強弱表現。

---
本技能由原 `stock-market-pro` 本地化重構，修正了 TWD 計價與台灣市場行情色彩習慣 (紅漲綠跌)。
