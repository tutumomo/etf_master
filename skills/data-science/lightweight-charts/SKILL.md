---
name: lightweight-charts
description: Integrate TradingView lightweight-charts (v5+) into web dashboards — candlestick, volume, technical indicator overlays, and fallback patterns.
---

# lightweight-charts Integration

## CDN
```html
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
```
Apache 2.0 license — attribution logo auto-displayed. Add HTML comment for clarity:
```html
<!-- lightweight-charts by TradingView — https://github.com/tradingview/lightweight-charts — Apache 2.0 License -->
```

## v5+ API (Current)

### Chart Creation
```js
const chart = LightweightCharts.createChart(container, {
    height: 420,
    layout: { background: { color: '#0f172a' }, textColor: '#94a3b8', fontSize: 12 },
    grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, timeVisible: true },
    crosshair: { mode: 0 },  // 0 = Normal (crosshair follows mouse)
});
```

### Candlestick Series
```js
const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#35d49a', downColor: '#ff6b81',
    borderUpColor: '#35d49a', borderDownColor: '#ff6b81',
    wickUpColor: '#35d49a', wickDownColor: '#ff6b81',
});
candleSeries.setData([
    { time: '2026-04-10', open: 80.0, high: 80.8, low: 79.95, close: 80.75 },
    // ...
]);
```

### Volume Histogram (Overlay on same chart)
```js
const volumeSeries = chart.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',  // separate price scale
});
chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },  // bottom 20% only
});
volumeSeries.setData([
    { time: '2026-04-10', value: 115520077, color: 'rgba(53,212,154,0.4)' },
    // color: green for up day, red for down day
]);
```

### MA Overlay Lines
```js
const smaSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#facc15',  // MA5=yellow, MA20=blue(#60a5fa), MA60=purple(#c084fc)
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false,
    title: 'MA5',
});
smaSeries.setData([{ time: '2026-04-10', value: 77.67 }, ...]);
```

### Sparkline (Minimal)
```js
const chart = LightweightCharts.createChart(container, {
    width: 100, height: 35,
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#94a3b8' },
    grid: { vertLines: { visible: false }, horzLines: { visible: false } },
    rightPriceScale: { visible: false },
    timeScale: { visible: false },
    handleScroll: false, handleScale: false,
});
const lineSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: priceUp ? '#35d49a' : '#ff6b81',
    lineWidth: 2,
    crosshairMarkerVisible: false,
});
```

## Key Patterns

### Fallback for Mixed Data Formats
When backend may return old `{t, c}` or new `{t, o, h, l, c, v}` data:
```js
const hasOHLCV = history[0] && history[0].o !== undefined;
if (hasOHLCV) {
    // Render Candlestick + Volume + MA overlays
} else {
    // Fallback to AreaSeries with {time, value} format
}
```

### Time Format Conversion
ISO datetime strings from backend need date-only for lightweight-charts:
```js
time: p.t.split('T')[0]  // '2026-04-10T00:00:00+08:00' → '2026-04-10'
```

### Volume Coloring
```js
const isUp = p.c >= p.o;  // close >= open = up day
color: isUp ? 'rgba(53,212,154,0.4)' : 'rgba(255,107,129,0.4)'
```

### NaN Handling (Backend)
Python `json.dumps` writes `NaN` which is invalid JSON. Replace before parsing:
```python
raw_text = path.read_text(encoding="utf-8").replace("NaN", "null")
data = json.loads(raw_text)
```
In JS: `value !== null && !isNaN(value)` filters, or `p.o != null` (loose null check for both null and undefined).

## Pitfalls

1. **API version**: v5 uses `chart.addSeries(LightweightCharts.CandlestickSeries, opts)` — NOT `chart.addCandlestickSeries()` (v3/v4 API)
2. **Volume scale margins**: Must call `chart.priceScale('volume').applyOptions({scaleMargins:{top:0.8,bottom:0}})` AFTER adding the series
3. **Data sorting**: lightweight-charts requires data sorted by time ascending
4. **Dedup check**: Before creating chart, check `container.querySelector('div.tv-lightweight-charts')` to avoid double-rendering
5. **Container clear**: Must `container.innerHTML = ''` before `createChart()` to remove loading placeholder