---
name: etf-market-context-pipeline
category: etf-tw
description: |
  3-phase roadmap to replace hardcoded market context with real data in the ETF_TW decision pipeline.
  Covers the full chain: event_context → market_context → decide_action → ai_decision_response.
  Phase A done in sandbox with dead DNS by leveraging existing shioaji data.
---

# ETF Market Context Pipeline — From Fake to Real

## Status (Updated 2026-04-13)

### Phase A: IN PROGRESS
- A1 ✅ `generate_market_event_context.py` v2 — derived from market_intelligence RSI/MACD/SMA/BB
- A2 ✅ `generate_taiwan_market_context.py` v2 — quant scoring with RSI dist/MACD breadth/SMA structure/volatility
- A3 🔲 `decide_action()` in `run_auto_decision_scan.py` — still needs yield/momentum/Sharpe dimensions
- A4 🔲 `reasoning` in ai_decision_bridge.py — still empty strings
- A5 🔲 Validation run
- A6 🔲 Commit + push

### Phase B/C: PENDING (need DNS)

## The Original Problem (Diagnosed 2026-04-13)

The entire decision chain produced "fake intelligence":

**Layer 1**: `generate_market_event_context.py` was ALL hardcoded (risk-off, elevated, high).
**Layer 2**: `generate_taiwan_market_context.py` was a quote-gap detector (zero price → cautious, else balanced).
**Layer 3**: `_pick_candidate()` was RSI-only picker — 00679B always won

## Full Pipeline Chain
```
generate_market_event_context.py  →  market_event_context.json
                                           ↓
generate_taiwan_market_context.py  →  market_context_taiwan.json
                                           ↓
run_auto_decision_scan.py         →  auto_preview_candidate.json
  (decide_action reads both contexts + market_intelligence)
                                           ↓
generate_ai_decision_response.py   →  ai_decision_response.json
  (_pick_candidate reads request inputs)
                                           ↓
dashboard / submit endpoint        →  actual order
```

## Key Files
- `scripts/generate_market_event_context.py` (46 lines, all hardcoded)
- `scripts/generate_taiwan_market_context.py` (89 lines, quote-gap + overlay)
- `scripts/generate_ai_decision_response.py` (91 lines, RSI-only picker + empty reasoning)
- `scripts/ai_decision_bridge.py` (213 lines, reasoning template with empty strings)
- `scripts/run_auto_decision_scan.py` (L234-488, decide_action + resolve_consensus)

## Available Data Sources (No DNS Needed)
- `market_intelligence.json` — shioaji-derived: RSI, MACD, MACD_signal, SMA5/20/60, BB_upper/mid/lower, last_price, history_30d for 14+ ETFs
- `intraday_tape_context.json` — market_bias, tape_summary, watchlist_signals
- `portfolio_snapshot.json` — cash, holdings, total_equity
- `market_cache.json` — live quotes (open/high/low/close/prev_close)
- `watchlist.json` — 18 ETFs with group assignments (core/income/defensive/growth/smart_beta)
- **shioaji live snapshots** — volume_ratio, change_rate, buy_price, sell_price, total_volume, total_amount (login via private/.env SINOPAC_API_KEY/SECRET_KEY, use `api.snapshots(list_of_contracts)`, NOT StreamIndexContracts object; use `os._exit(0)` not `api.logout()` to avoid segfault)

## Additional Data Sources (DNS Required — Phase B)
- `stock-market-pro-tw/scripts/news.py` — TW stock news search
- `stock-market-pro-tw/scripts/ddg_search.py` — DDG news search (needs `ddgs` package)
- `stock-analysis-tw/scripts/hot_scanner.py` — Market hot spot scanner
- `stock-analysis-tw/scripts/rumor_scanner.py` — Early signal detector
- yfinance: ^TWII, ^VIX, TWD=X, SOXX, ^TNX (needs DNS)

## A-1/A-2 Architecture (v2, implemented)

### generate_market_event_context.py v2
```
market_intelligence.json
  → _compute_market_breadth() → bullish_pct, bearish_pct, avg_rsi, avg_macd_hist
  → _determine_regime() → event_regime, global_risk_level, geo_political_risk, rate_risk, energy_risk
  → _compute_defensive_bias() → defensive_bias
  → _detect_active_events() → active_events[] (overbought/oversold/MACD divergence)
  → _generate_summary() → Chinese summary string
  → market_event_context.json
```

### generate_taiwan_market_context.py v2
```
market_intelligence.json + market_event_context.json + strategy_link.json
  → _compute_rsi_distribution() → avg, overbought/oversold pct
  → _compute_macd_breadth() → bullish/bearish pct, direction
  → _compute_sma_structure() → bull/bear aligned, above/below sma20
  → _compute_volatility() → 30d annualized vol per symbol
  → _compute_group_trends() → avg RSI/MACD per group (core/income/defensive/growth)
  → _determine_regime_from_signals() → scored -5..+5 → regime/tilts
  → market_context_taiwan.json (with new quant_indicators section)
```

### Key Design: quant_indicators section in output
```json
{
  "quant_indicators": {
    "rsi_distribution": {"avg": 55.2, "overbought_pct": 15.4, "oversold_pct": 7.7},
    "macd_breadth": {"bullish_pct": 60.0, "direction": "bullish"},
    "sma_structure": {"above_sma20_pct": 69.2, "structure": "bullish"},
    "volatility": {"avg_annual": 0.18, "high_vol": [], "low_vol": []},
    "group_trends": {"core": {"avg_rsi": 58, "momentum": "bullish"}, ...},
    "regime_score": 1
  }
}
```

## 3-Phase Fix Plan

### Phase A: Derive Event Context from Real Technical Data (No DNS) — IN PROGRESS
- A1 ✅ market_event_context derived from RSI/MACD/SMA/BB breadth signals
- A2 ✅ market_context_taiwan scored from quant indicators with real thresholds
- A3 🔲 decide_action() needs yield/momentum/Sharpe multi-factor scoring
- A4 🔲 reasoning strings need real market narrative (not empty)
- A5 🔲 Full pipeline validation run
- A6 🔲 Git commit + push

### Phase B: External News & Indicators (Needs DNS)
- DDG/RSS news → event labels
- TAIEX, VIX, TWD/USD real-time
- FOMC/central bank calendar
- Foreign institutional flow data (if available via shioaji)

### Phase C: LLM-Augmented Reasoning
- Feed real data + news summary to LLM
- LLM produces structured `market_event_context` with qualitative judgment
- LLM produces `reasoning` strings with actual geopolitical/economic analysis

## Pitfalls
- **DNS death in sandbox**: Cannot install packages or fetch external URLs. Always have a no-DNS fallback path using shioaji data.
- **Use existing skills**: stock-market-pro-tw and stock-analysis-tw are already installed. Don't reinvent yfinance calls.
- **教訓10**: verify `broker_order_id` exists after any submit — fake receipts have empty ids.
- **教訓15**: dashboard state path is always `instances/etf_master/state/`.
- **教訓17**: git push must be done on real terminal (sandbox osxkeychain broken).