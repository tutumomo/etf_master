# Lightweight Charts 併入 ETF_TW 整合方案

> 生成日期：2026-04-12
> lightweight-charts 版本：v5.1
> GitHub：https://github.com/tradingview/lightweight-charts
> 文件：https://tradingview.github.io/lightweight-charts/

## 現狀盤點

### Dashboard 已使用 lightweight-charts
- CDN 載入：`https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js`
- 位於 `dashboard/templates/overview.html` 第 3 行
- 總計 926 行 HTML，含大量 Jinja2 模板

### 目前圖表使用
1. **Sparkline（迷你走勢圖）**：LineSeries, 100x35px, 30 日收盤價
   - `overview.html` 第 750-771 行
   - 無時間軸、無十字線、無交互
   - 漲綠跌紅配色

2. **Large Chart（詳情展開圖）**：AreaSeries, 300px 高, 收盤價面積圖
   - `overview.html` 第 828-849 行
   - 有時間軸但無十字線 tooltip
   - 單色漸層配色

### 後端資料現況
- API `/api/history/{symbol}` 只回傳 `{symbol, history: [{t, c}]}`
- 但 `sync_ohlcv_history.py` 實際抓了完整 OHLCV（Open/High/Low/Close/Volume）
- 也有技術指標計算：MA5/MA20/MA60, RSI, MACD, BBands
- 這些資料存在 `market_intelligence.json` 但前端未渲染

### 關鍵發現
**後端已有完整 OHLCV + 技術指標資料，但前端只用了收盤價畫線圖。** 改動集中在 API 回傳欄位擴充 + 前端渲染邏輯升級，後端不需要大動。

---

## Phase 1：K 線圖 + 成交量（優先實作）

### 目標
把隱藏的 OHLCV 資料充分展現，視覺質感跳躍式提升。

### 改動範圍

#### 1. API 擴充 — `app.py`
```python
# /api/history/{symbol} 擴充回傳
# 原本：只有 {t, c}
# 改為：{t, o, h, l, c, v} + 指標 {ma5, ma20, ma60, rsi, macd, macd_signal, macd_hist}
```

需要從 `market_intelligence.json` 讀取完整資料，不僅是 `history_30d`。

#### 2. 前端 Large Chart 升級 — `overview.html`

將 AreaSeries 替換為 CandlestickSeries + 成交量：

```javascript
const chart = LightweightCharts.createChart(container, {
    height: 300,
    layout: { background: { color: '#0f172a' }, textColor: '#94a3b8' },
    grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, timeVisible: true },
    attributionLogo: true,  // 授權要求
});

// K 線主圖
const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#35d49a',
    downColor: '#ff6b81',
    borderVisible: false,
    wickUpColor: '#35d49a',
    wickDownColor: '#ff6b81',
});
candleSeries.setData(ohlcvData.map(d => ({
    time: d.time,
    open: d.o, high: d.h, low: d.l, close: d.c
})));

// MA5 疊加
const ma5Series = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#f5c542', lineWidth: 1, title: 'MA5',
    priceLineVisible: false, lastValueVisible: false,
});
ma5Series.setData(filterValid(maData.filter(d => d.ma5)));

// MA20 疊加
const ma20Series = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#7cd6ff', lineWidth: 1, title: 'MA20',
    priceLineVisible: false, lastValueVisible: false,
});

// 成交量（overlay on price scale）
const volumeSeries = chart.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',  // 獨立价格刻度
});
volumeSeries.priceScale().applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
});
volumeSeries.setData(volumeData);

chart.timeScale().fitContent();
```

#### 3. Sparkline 保持不變
現有 LineSeries sparkline 效能好、資訊密度高，不需改動。

---

## Phase 2：技術指標子圖

### 目標
RSI / MACD 專用子圖面板，完整技術分析圖。

### Pane API（v5.1 新功能）
```javascript
// 主圖 + MA + BBands（已有）
// 子圖 1：成交量
const volumePane = chart.addPane({ minH: 80 });
// 子圖 2：RSI
const rsiPane = chart.addPane({ minH: 100 });
// 子圖 3：MACD
const macdPane = chart.addPane({ minH: 100 });
```

### API 需新增指標回傳
`/api/history/{symbol}` 需新增：
- `rsi_values`: RSI 14 序列
- `macd_values`: MACD line 序列
- `macd_signal`: Signal line 序列
- `macd_hist`: Histogram 序列

---

## Phase 3：互動與即時更新

### 目標
從靜態快照進化到可互動監控面板。

1. **十字線 + Tooltip**：hover 顯示 OHLCV 數值
2. **即時更新**：`series.update(newTick)` + SSE endpoint
3. **時間軸控制**：1D / 1W / 1M / All 切換
4. **Timezone**：`timeZone: 'Asia/Taipei'`

### SSE Endpoint 範例
```python
@app.get("/api/stream/{symbol}")
async def stream_price(symbol: str):
    # Server-Sent Events for real-time price updates
    ...
```

---

## Phase 4：進階功能

1. **交易標記 Plugin**：K 線上標記買賣點（paper_ledger / orders_open）
2. **風控警示線**：止損線、成本均線（positions.json 均價）
3. **多標的對比**：疊加兩檔 ETF 歸一化走勢圖（% change）

---

## 授權注意

lightweight-charts 是 Apache 2.0 License，但要求 attribution：
- 頁面上必須顯示 TradingView 來源連結
- 可用 `attributionLogo: true` 自動在圖表上顯示 logo
- NOTICE 檔案包含 attribution 文字

## 相關檔案路徑

| 檔案 | 用途 |
|------|------|
| `dashboard/templates/overview.html` | 前端主模板，圖表渲染邏輯 |
| `dashboard/templates/base.html` | 基礎模板 |
| `dashboard/app.py` | FastAPI 後端，API 路由 |
| `scripts/sync_ohlcv_history.py` | OHLCV 資料同步 + 技術指標計算 |
| `scripts/refresh_monitoring_state.py` | 監控狀態刷新 |
| `instances/<agent_id>/state/market_intelligence.json` | 市場指標資料（含 history_30d + indicators） |

## 實作優先順序

| 階段 | 工作量 | 影響力 | 時程 |
|------|--------|--------|------|
| Phase 1 | 中 | 高 | 1-2 天 |
| Phase 2 | 中 | 高 | 1-2 天 |
| Phase 3 | 中高 | 中 | 2-3 天 |
| Phase 4 | 高 | 中高 | 3-5 天 |