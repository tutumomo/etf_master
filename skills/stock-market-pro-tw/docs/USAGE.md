# Stock Market Pro TW 使用說明 (USAGE.md)

`stock-market-pro-tw` 是一個針對台灣股市與 ETF 優化的專業級命令行工具，提供即時報價、基本面分析、以及可自訂多種技術指標的高解析度圖表。

## 核心子指令說明

### 1. `price` (預設指令)
取得指定標的的即時股價、漲跌額與漲跌幅。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py price 0050.TW
# 或者省略 'price'
uv run skills/stock-market-pro-tw/scripts/yf.py 2330.TW
```

### 2. `fundamentals`
查看關鍵基本面指標，包含：市值 (Market Cap)、預估 PE (Forward PE)、EPS (每股盈餘) 與 ROE (股東權益報酬率)。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py fundamentals 0056.TW
```

### 3. `history`
在終端機中以 ASCII 藝術形式快速呈現股價歷史走勢圖。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py history 00878.TW 6mo
```

### 4. `pro` (專業圖表生成)
生成包含技術指標的高品質 PNG 線圖。
- **指標參數**: `--rsi`, `--macd`, `--bb`, `--vwap`, `--atr`。
- **圖表類型**: `candle` (K 線) 或 `line` (折線)。

```bash
# 生成 1 年期的 K 線圖，包含 RSI、MACD 與 布林通道
uv run skills/stock-market-pro-tw/scripts/yf.py pro 2330.TW 1y candle --rsi --macd --bb
```

### 5. `report`
一鍵生成綜合診斷報告，包含：
- 報價與基本面摘要文字。
- 自動生成一張包含 RSI+MACD+BB 的技術線圖。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py report 0050.TW 3mo
```

---

## 輔助工具

### 新聞掃描 (`news`)
針對指定標的搜尋台灣本地財經新聞。
```bash
uv run skills/stock-market-pro-tw/scripts/news.py 2330.TW
```

### 期權異動 (`option`)
偵測大額期權流向與異常波動（僅限部分大型權值股或 ETF）。
```bash
uv run skills/stock-market-pro-tw/scripts/yf.py option 0050
```

---

## 參數快速參考

| 參數 | 說明 |
|---|---|
| `symbol` | 標的代碼，台股請加 `.TW` (上市) 或 `.TWO` (上櫃) |
| `period` | 時間範圍：`1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `5y`, `max` |
| `--rsi` | 加入 RSI(14) 相對強弱指標 |
| `--macd` | 加入 MACD(12, 26, 9) 指數平滑異同移動平均線 |
| `--bb` | 加入布林通道 (Bollinger Bands, 20, 2) |
| `--vwap` | 加入成交量加權平均價 (VWAP) |
| `--atr` | 加入平均真實波幅 (ATR, 14) |
