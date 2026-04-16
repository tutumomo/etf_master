---
name: etf-decision-engine-v2
description: "ETF_TW decision engine v2 rewrite — replacing hardcoded values with real quantitative data (RSI/MACD/breadth → regime, momentum/sharpe/yield → scoring) + external data sources + LLM-enhanced reasoning"
version: "3.0"
last_updated: "2026-04-14"
---

# ETF Decision Engine V2 Rewrite

Multi-phase rewrite of the ETF_TW decision engine. Replace hardcoded values with real quantitative data, external market data sources, and LLM-enhanced reasoning. Based on TOMO's three buying principles: 1) value undervalued 2) promising outlook 3) good track record.

## Architecture: Full Pipeline

```
sync_ohlcv_history.py → market_intelligence.json (per-symbol indicators)
  ↓
sync_macro_indicators.py → macro_indicators.json (TAIEX trend, VIX proxy, breadth)
  ↓
sync_central_bank_calendar.py → central_bank_calendar.json (FOMC/央行 dates)
  ↓
sync_news_from_local.py → news_digest.json (RSS keywords + sentiment)  [REQUIRES REAL TERMINAL]
  ↓
generate_market_event_context.py → market_event_context.json (regime/risk)
  ↓
generate_taiwan_market_context.py → market_context_taiwan.json (regime/tilts/scoring)
  ↓
generate_llm_event_context.py → market_event_context.json (LLM-enhanced regime)
  ↓
generate_llm_decision_reasoning.py → decision_reasoning.json (LLM market/risk assessment)
  ↓
run_auto_decision_scan.py decide_action() → auto_preview_candidate.json
  ↓
generate_ai_agent_response.py → ai_decision_response.json (final output)
```

## Phase A: TOMO三原則量化 ✅ (commit 2651aa8)

### A1: generate_market_event_context.py v2
- Derives from `_compute_market_breadth()` (RSI/MACD/SMA/BB)
- Source tag: `event-context-derived-v2`

### A2: generate_taiwan_market_context.py v2
- Quantitative scoring system (-5 to +5) with RSI distribution, MACD breadth, SMA structure, volatility, group trends
- Source tag: `taiwan-market-context-v2`

### A3: decide_action() — TOMO three principles quantified
- `_score_yield()` / `_score_momentum()` / `_score_track_record()` replace scattered ifs
- Group base scores: core=2, income=2, defensive=2, growth=1.5, smart_beta=1.5
- Not-held bonus: 1/√(group_size) — diluted by intra-group competition (教訓20)
- Each candidate gets `dimension_scores: {yield, momentum, track_record}` for dashboard
- Validated: 00892=#1 (6.58), 00679B bias solved

### A4: sync_ohlcv_history.py Updated
- Added `calc_momentum()`, `calc_sharpe()`, `calc_yield_from_close()`
- New fields: momentum_20d, sharpe_30d, return_1y

### A5: AI agent reasoning
- Builds reasoning from quant_indicators, not empty shell

## Phase B: External Data Sources ✅ (commit 64807c9)

### B1: sync_news_from_local.py
- RSS scraper: cnyes + yahoo finance
- Keyword tags: rate_decision, geo_risk, earnings, etf_related, market_sentiment, sector_tech, sector_finance
- Simple sentiment scoring
- **REQUIRES REAL TERMINAL** (sandbox HTTPS outbound blocked)
- Run: `cd ETF_TW && OPENCLAW_AGENT_NAME=etf_master .venv/bin/python3 scripts/sync_news_from_local.py`

### B2: sync_macro_indicators.py
- TAIEX trend (up/down/sideways from shioaji)
- VIX proxy (from market_intelligence annualized vol, NOT real VIX index)
- Market breadth (needs live snapshots, falls back to "unknown")

### B3: sync_central_bank_calendar.py
- Hardcoded 2026 FOMC + 央行 dates (sandbox can't scrape)
- Outputs: upcoming events, next_major, days_until_next

### B4: generate_market_event_context.py patched
- Central bank meeting ≤7 days → elevate rate_risk to high, global_risk to moderate
- VIX proxy >25 → elevate risk level + shift regime to cautious
- `geo_risk` tags ≥3 → geo_political_risk=high; ≥1 → medium
- News sentiment bias → adjust event layer

## Phase C: LLM-Enhanced Reasoning ✅ (commit 6ad0c29)

### C1: generate_llm_event_context.py
- LLM-enhanced event context with rule-engine fallback
- Reads: news + macro + calendar + intelligence → builds LLM prompt → structured output
- When LLM unavailable → `_rule_fallback()` generates from same data

### C2: generate_llm_decision_reasoning.py
- LLM-enhanced decision reasoning generator
- Outputs: market_analysis, risk_assessment, position_guidance, llm_reasoning, confidence
- `_build_rule_based_reasoning()` fallback auto-generates from event_ctx+macro+calendar+news+intel

### C3: _build_agent_reasoning() integration
- Loads `decision_reasoning.json` as `pre_reasoning`
- Populates reasoning dict fields from `pre_reasoning` (market/risk/position context)
- Falls back to inline computation if `pre_reasoning` unavailable
- `reasoning_source` tag: `llm-enhanced-v1` | `rule-engine-v1` | `inline`

## Critical: _call_llm() Design Pattern

The LLM call function uses a 3-strategy fallback chain:

1. **Ollama HTTP API (localhost:11434)** — FIRST priority, fastest, local
   - Check daemon alive: `GET /api/tags`
   - Chat: `POST /api/chat` with `stream: False`
   - Model: `glm-5:cloud` (TOMO specified)
   - Timeout: 30s for generation, 3s for daemon check
   
2. **OpenAI-compatible cloud API** — second, via env vars `LLM_API_BASE`/`LLM_API_KEY`
   - Timeout: 8s (short, sandbox HTTPS may be blocked)
   
3. **Ollama CLI** — LAST resort only
   - `ollama run <model> <prompt>` — **may hang in sandbox subprocess**
   - Only attempt if `ollama list` succeeds (daemon alive check)
   - Timeout: 15s

**Why this order matters**: 
- `ollama run` CLI blocks the subprocess and can hang indefinitely in sandboxed environments
- HTTP API to localhost works even when external HTTPS is blocked
- `shutil.which('ollama')` returns the binary even if daemon is down, so always check daemon health first

## Sandbox DNS Fix — 雙層修法 (2026-04-14)

### 根因
`scutil --dns` → "No DNS configuration available"，macOS 系統 DNS resolver 在沙盒內完全失效。
`/etc/resolv.conf` 有 8.8.8.8 但 macOS 不讀（只看 scutil）。
無 sudo 權限，無法修改 /etc/hosts 或重啟 mDNSResponder。

### 修法 1：Python 層 (dns_fix.py)
`scripts/dns_fix.py` — raw UDP DNS query (port 53 to 8.8.8.8) + monkey-patch `socket.getaddrinfo`。
已注入：sync_etf_universe_tw.py, sync_news_from_local.py, generate_llm_event_context.py,
generate_llm_decision_reasoning.py, run_auto_decision_scan.py, news_crawler.py。
**自動行為**：patch() 先測系統 DNS，正常就 return，損壞才套用。永遠零幹擾。

### 修法 2：系統層 (/etc/hosts)
沙盒 git/curl/pip 走系統 DNS，需要 /etc/hosts 靜態映射。
使用者需在本機終端機執行（sudo 寫入）：
```
curl https://gist.githubusercontent.com/tuchengshin/.../hosts.txt | sudo tee -a /etc/hosts
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```
關鍵 domain：google.com, github.com, news.cnyes.com, finance.yahoo.com, pypi.org, www.twse.com.tw
**注意**：/etc/hosts 裡舊 IP 殘留會造成 TCP timeout（curl 會停在連線階段），
務必用 `grep -n` 確認無重複 domain，並刪除舊 IP 行。

### 外部進程 vs Python
- Python：吃 dns_fix.py monkey-patch，自動繞過損壞的 DNS
- git / curl / pip：走系統 DNS，必須靠 /etc/hosts
- opencli browser：走 Chrome CDP daemon，完全不受影響

## 已知 bug

### `/api/intelligence` warning: tracked symbols exist but intelligence payload is empty
`dashboard/app.py` 的 `/api/intelligence` endpoint 有 warning，但 `/api/overview` 的 intelligence 是完整的。
懷疑是 market_intelligence.json 格式問題或 endpoint 讀取邏輯有誤，尚未修。
** workaround**：用 `/api/overview` 取代 `/api/intelligence`。

### generate_llm_decision_reasoning.py 的 `from __future__` 順序
第二個 `from __future__ import annotations` 錯誤地出現在 docstring 後，造成 SyntaxError。
症狀：直接執行 script 回 500 或错误输出。
每次修改 script 都要確認 `from __future__` 在 shebang 後第一行。

## State Path Resolution Gotchas (多實例狀態污染)

### 問題
當系統中建立 multiple agent instances (etf_master, etf_son, etf_wife) 時，
Dashboard 和 Scripts 如果沒有 `OPENCLAW_AGENT_NAME` 環境變數，
會自動 fallback 到 `etf_master`，造成跨實例的狀態讀寫污染。

### 解決方案
1. **Dashboard 修法**: `dashboard/app.py` 開頭強制設定（import 前）
```python
import os
if not os.environ.get('OPENCLAW_AGENT_NAME') and not os.environ.get('AGENT_ID'):
    os.environ['OPENCLAW_AGENT_NAME'] = 'etf_master'
    os.environ['OPENCLAW_AGENT_NAME_FORCED'] = 'true'
```

2. **Scripts**: 確保所有命令都有 `OPENCLAW_AGENT_NAME=etf_master` prefix
3. **API 端點**: `/api/overview` 和 `/api/intelligence` 使用不同狀態目錄檢查邏輯

### 偵測症狀
- Dashboard 顯示數據和 cli script 輸出不一致
- `/api/intelligence` 回傳 warning 但 `/api/overview` 有完整數據
- 某個 agent 的決策出現在另一個 agent 的 API 輸出中

### 驗證方法
```bash
cd ETF_TW && \
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python3 -c \"
from scripts.etf_core import context
print('instance:', context.get_instance_id())
print('state dir:', context.get_state_dir())
\"
```

## Sandbox Network Gotchas

- DNS resolves fine but TCP 443 connections fail (HTTP/HTTPS = 000)
- `ollama list` works (local daemon), `ollama run` may hang in subprocess
- ollama HTTP API (localhost:11434) works because it's local, not external
- shioaji WebSocket to Sinopac works (special route)
- `git push` fails in sandbox (osxkeychain no interaction permission) → use real terminal
- News via opencli browser always works (Chrome CDP daemon)

## Shell Execution Prefix

```bash
cd /Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW && \
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python3 scripts/<script>.py
```

State dir: `instances/etf_master/state/` (NOT `ETF_TW/state/` — dashboard reads from instances/)

## DNS / 網路修法

See section above "Sandbox DNS Fix — 雙層修法" for full details on the dual-layer approach.

## Phase D: sizing_engine_v1 + Decision Traffic Lights ✅ (2026-04-14)

### D1: Replace placeholder preview sizing with real guardrail sizing
- `scripts/sizing_interface.py` upgraded from `build_placeholder_preview_sizing()` only
  to a reusable real calculator:
  - `build_preview_sizing()`
  - `build_preview_sizing_from_context()`
- Inputs:
  - cash available
  - total equity
  - current position value
  - max position concentration cap
  - max single-order cap
  - cash buffer
  - min trade unit
  - odd-lot allowed
  - risk_temperature multiplier
- Outputs (stable schema for UI/API):
  - `quantity`
  - `quantity_mode = sizing_engine_v1`
  - `sizing_engine = sizing_engine_v1`
  - `sizing_status = ok|blocked`
  - `can_order`
  - `limit_reasons`
  - `estimated_order_value`
  - `budget_breakdown`
  - `policy_used`
  - `order_unit`
  - `quantity_note`

### D2: Wiring points
- `run_auto_decision_scan.py`
  - replace placeholder sizing with `build_preview_sizing_from_context()`
  - if sizing fails, keep preview but annotate/block via risk note
  - `preview-sizing-blocked` is only used when sizing is the primary blocker; do not overwrite `preview-locked`
- `generate_ai_agent_response.py`
  - AI candidate also runs through the same sizing engine
  - this keeps Rule Engine and AI Bridge on the same quantity/risk semantics

### D3: Decision dashboard traffic-light cards
- `dashboard/app.py` adds `build_decision_traffic_lights()`
- `dashboard/templates/overview.html` renders 3 cards:
  - Rule Engine
  - AI Bridge
  - Consensus
- Color semantics:
  - green = usable / fresh / no hard conflict
  - yellow = no candidate yet / downgraded confidence / waiting
  - red = locked conflict / stale AI / sizing blocked
- This is intentionally summary-first so TOMO can see risk state without reading long detail blocks.

### D4: UI fields to expose whenever sizing_engine_v1 is present
For preview candidate and AI candidate, surface at least:
- `quantity`
- `quantity_mode`
- `sizing_status`
- `can_order`
- `estimated_order_value`
- `limit_reasons`
- `quantity_note`

### D5: Testing pattern that caught regressions
Add focused tests instead of relying only on manual dashboard inspection:
- unit test sizing blocked by concentration cap
- unit test odd-lot safe quantity when budget allows
- dashboard API test exposing `decision_traffic_lights`
- dashboard logic test for locked consensus => red traffic light
- AI agent response test asserting candidate carries `quantity_mode = sizing_engine_v1`

### D6: Key lesson
Do NOT stop at adding a helper function named like a future interface.
If the UI already shows quantity, the sizing layer must produce real gateable fields (`can_order`, `limit_reasons`, `sizing_status`) and both decision chains must consume the same contract.
Otherwise dashboard users will mistake placeholders for executable advice.

## Remaining / Future

- `/api/intelligence` warning bug — investigate endpoint logic, use `/api/overview` as workaround
- Strategy weight matrix (教訓25): decide_action group=散裝 if needs weight_matrix.json
- watchlist yield_pct: architecture ready, data source not connected
- Git push: always from real terminal: `cd <ETF_TW> && git push origin main`
- market_intelligence return_1y: some ETFs show None (insufficient history)
- generate_llm_decision_reasoning.py `from __future__` must be FIRST line after shebang — always verify when editing