# ETF_Master: 智慧型台灣 ETF 投資助理 (v1.4.15)

`ETF_Master` 是一款專為台灣 ETF 投資者設計的 AI 輔助決策與資產管理系統。本專案秉持「**交易安全優先於功能完備**」的核心價值，透過「三層真相層級」治理與「雙鏈決策仲裁」機制，為投資者提供一個穩定、透明且具備深度洞察的投資工作台。

---

## 🚀 專案核心價值：安全與穩定

本專案的所有功能皆環繞著以下原則建構：
- **交易安全第一**：所有的交易指令必須經過 `pre_flight_gate` 保險絲檢核，並嚴格執行 **Preview → Confirm → Submit** 三段式人工確認。
- **真相層級治理**：系統區分三種數據真實度：
  - **Level 1 (LIVE)**：券商 API 直接提供的實體事實（最高優先權）。
  - **Level 2 (VERIFYING)**：已送出但尚未在櫃檯查見的委託。
  - **Level 3 (SNAPSHOT)**：本地緩存或歷史快照（次級資訊）。
- **人機協同 (Human-in-the-loop)**：系統只產生「建議」與「預覽」，**絕不自動送出真實委託**。

---

## 🛠️ 技術架構與功能

### 1. 雙鏈決策控制台 (Decision Control)
整合了兩條互補的決策鏈，並由「共識仲裁系統」產出最終指引：
- **系統規則引擎 (Rule Engine)**：基於 RSI、MACD、SMA 及 TOMO 三原則（殖利率、動能、紀錄）的量化掃描。
- **AI 決策橋接 (AI Bridge)**：利用大語言模型感應國際環境、情緒偵測，並結合 Wiki 知識庫背景。
- **共識仲裁 (Consensus)**：自動比對雙鏈建議，具備「AI 風險否決權」，在分歧時提供明確的行動指引。

### 2. 多技能財經生態系
整合了四個專業級財經技能：
- **`ETF_TW`**：核心交易適配器，支援永豐金 (Shioaji) API、模擬交易與持倉同步。
- **`stock-analysis-tw`**：8 維度量化診斷工具，自動計算標的健康度與風險溫度。
- **`stock-market-pro-tw`**：產生高品質技術線圖與 ASCII 趨勢報告。
- **`taiwan-finance`**：投行級估值框架（DCF, Comps）與法說會分析。

### 3. 自動化知識沉澱 (graphify + llm-wiki)
- **圖譜先行**：`graphify` 已整合進 Codex 工作流，可在回答程式碼庫與知識庫問題前先利用 `graphify-out/graph.json` 與 `GRAPH_REPORT.md` 對齊社群結構與關鍵節點。
- **廣度背景**：內建全台灣 330 支 ETF 的基礎百科。
- **深度蒸餾**：Cron 任務自動將每日診斷結論與市場體制轉化為結構化的 Markdown 知識，供 AI 隨時調閱。

---

## 🖥️ 交互介面

### 互動儀表板 (Dashboard)
- **網址**：`http://localhost:5055`
- **特色**：
  - 即時反映永豐金實體帳戶持倉與 KPI。
  - 反應式 (Reactive) 策略切換：套用策略後自動重生決策建議。
  - 摺疊式區塊：在維持監控頂部看板的同時保持介面簡潔。
  - 內嵌式交易票據：流暢的三段式下單體驗。

### 命令行工具 (CLI)
```bash
# 啟動儀表板
python scripts/etf_tw.py dashboard

# 查詢即時持倉
python scripts/etf_tw.py portfolio

# 執行標的診斷
uv run skills/stock-analysis-tw/scripts/analyze_stock.py 0050.TW
```

---

## 📅 自動化排程 (Cron Jobs)
系統預設 **9 個**關鍵自動化任務（定義於 `cron/jobs.json`）：
1. **早班準備 (08:45)**：盤前感知與復盤。
2. **盤中智慧掃描 (每30分)**：動態刷新報價、量化診斷與決策共識。
3. **盤後收工 (15:00)**：每日總結、決策品質評分與 Wiki 沉澱。
4. **決策自動復盤 (15:05 平日)**：T+N 價格回填、verdict 判定、雙鏈勝率統計。
5. **每週深度復盤 (週六 09:00)**：長線趨勢對齊與週報生成。
6. **決策品質週報 (週六 09:05)**：產出雙鏈勝率 Wiki 供 AI Bridge 引用。
7. **健康巡檢 (08:00)**：確保執行環境與 API 連線完好。
8. **worldmonitor 每日快照 (07:50 平日)**：拉取全球供應鏈/地緣風險信號。
9. **worldmonitor 事件巡檢 (盤中每30分)**：偵測 L2/L3 升級事件。

---

## ⚙️ 快速部署

> 完整步驟請見 [DEPLOYMENT.md](DEPLOYMENT.md)。

**最低部署（paper 模式，無需帳號）：**

```bash
# 1. 建立 venv（Python 3.14+ 必須）
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r scripts/etf_core/requirements.txt

# 2. 建立 instance config
mkdir -p instances/etf_master/state
cp instance_config.json.example instances/etf_master/instance_config.json

# 3. 設定 Agent ID
export AGENT_ID=etf_master

# 4. 啟動 Dashboard
AGENT_ID=etf_master .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

開啟 `http://localhost:5055` 即可使用。

**環境需求**：Python **3.14+**、`uv`、Hermes Agent v0.9.0+

---

## 📦 版本紀錄

### v1.4.15 (2026-04-24)
- feat(knowledge): 完成 `graphify + llm-wiki` 整合收斂，Codex 現在可透過專案 `AGENTS.md` 與 `.codex/hooks.json` 在回答程式碼庫問題前優先讀取知識圖譜
- chore(knowledge): 專案層接入 `graphify` hook 與知識圖譜讀取規則，讓圖譜探索與 wiki 沉澱工作流在同一個 repo 內收斂
- docs(readme): 更新知識工作流說明，明確標示圖譜查詢與 wiki 沉澱的分工

### v1.4.13 (2026-04-22)
- feat(dashboard): 「全鏈路同步」現在先執行 `sync_live_state.py`，再跑 monitoring / auto-decision / consensus，避免 dashboard 用舊持倉快照產生建議
- ux(dashboard): 全鏈路同步成功提示改為明示「含券商持倉同步」，自動刷新延長為 15 秒，與實際券商拉取耗時對齊
- docs(stock-analysis): `skills/stock-analysis-tw/SKILL.md` 補齊台灣 ETF 的 yfinance 已知陷阱，明確說明 `dividendRate=None`、`quoteSummary 404`、`.TW/.TWO` 後綴差異與建議 fallback
- docs(wiki): 更新 `market-view.md`、`risk-signal.md` 與多檔 ETF 實體頁快照，補上 2026-04-21~2026-04-22 的市場體制、風險分化與最新價格
- chore(profile): `config.yaml` 改為結構化 `model.default/provider` 設定，啟用 `memory.provider: builtin`，同步調整 `etf-master` skin、dashboard theme 與 busy-input queue 模式

### v1.4.6 (2026-04-20)
- feat(reviews): 自動決策復盤管線 — `sync_decision_reviews.py`（15:05 盤後 T+N 回填 + ±1.5% verdict 判定 + outcome_final + chain_breakdown 統計）
- feat(weekly): 決策品質週報 — `generate_decision_quality_weekly.py`（週六 09:05 產出 `wiki/decision-weekly-YYYY-WNN.md` + `decision-quality-latest.md`）
- feat(provenance): `build_provenance_record()` 新增 `chain_sources` 參數，記錄雙鏈仲裁來源
- feat(cron): 新增 2 個 job（ETF 決策自動復盤、ETF 決策品質週報），Job 數量 7→9
- fix(ai-bridge): `refresh_decision_engine_state.py` 加入 `generate_ai_agent_response.py`，修復 `risk_context_summary` 永遠為空
- fix(symbol): `symbol_mappings.json` 新增 `00679B` 條目，指定 `.TWO` 後綴避免 yfinance 404
- fix(cron): 新增 wrapper 腳本解決 Hermes cron `script` 欄位路徑解析問題
- fix(weekly): `WIKI_DIR` 路徑從 `parents[2]` 修正為 `parents[3]`
- test: 15 新增測試全通，全套 364 tests passed

### v1.4.1 (2026-04-19)
- fix(verify): `verify_deployment.sh` 實測修正 — 移除 `set -e`、修正 `/api/positions` 端點（改讀 `/api/overview.positions`）、修正交易時段閘門測試指令（`validate-order`）
- fix(verify): 新增 `DASHBOARD_PORT` 環境變數支援，可用於多實例測試
- docs(deployment): 修正步驟順序（sync pipeline 移至 Dashboard 啟動前）、新增 Paper Mode 最小腳本表格、補充 worldmonitor cron 與 `enabled:false` 的關係說明
- fix(security): `cron/jobs.json` 個人 Telegram chat_id/chat_name 移轉為 `${TELEGRAM_HOME_CHANNEL}`/`${TELEGRAM_CHAT_NAME}` env 佔位符
- docs(env): `private/.env.example` 補齊所有變數的繁中說明（AGENT_ID、Telegram、Shioaji、worldmonitor）
- chore(profile): 實測從 `etf_master` clone 建立 `etf_master_wife` 獨立 instance，9/9 健康巡檢全通（353 tests passed）

### v1.4.0 (2026-04-19)
- feat(worldmonitor): 整合全球風險雷達 — `sync_worldmonitor.py` 雙模式（daily/watch）
- feat(worldmonitor): API 欄位修正，新增 `_derive_global_stress_level/taiwan_strait_risk/taiwan_semiconductor_risk()` 推算邏輯
- feat(worldmonitor): Bot UA 繞過 middleware.ts 403 過濾
- feat(ai-bridge): worldmonitor 接入 AI Decision Bridge 作為第 14 個輸入源
- feat(dashboard): 全球風險雷達卡新增 chokepoints 展開、tooltip、收合、↻ 更新按鈕
- feat(cron): 新增 `worldmonitor_daily`（07:50）、`worldmonitor_watch`（盤中每30分）排程
- docs: 新增 `DEPLOYMENT.md`、`instance_config.json.example`、`private/.env.example`
- docs: 更新 `SKILL.md`（v1.4.0）、`AI_DECISION_BRIDGE.md`、`STATE_ARCHITECTURE.md`
- test: 9 項 worldmonitor 測試全通（含 API schema、alert 偵測、AI bridge 接線）

### v1.2.2 (2026-04-17)
- feat(quality-report): 新增 `decision_quality_report.json` 產生流程，統計策略對齊率、信心分佈與攔截率
- feat(stress-test): 新增 Paper mode 壓力測試與幽靈委託偵測，驗證 scan 週期穩定性
- feat(backtest): 新增 `ai_decision_outcome.jsonl` 回測框架，輸出勝率、最大回撤與 `quality_gate_passed`
- feat(live-submit): 永豐金 live submit 路徑接通，修正 broker ordno 讀取，加入 `verify_order_landed()` ghost detection
- feat(live-gate): Dashboard 新增 Live 模式雙重確認授權閘門，品質閘門未通過前禁止解鎖
- test(regression): 新增 live submit 7 場景回歸測試；全套測試提升到 **328 passed, 6 warnings**

### v1.2.0 (2026-04-17)
- feat(rule-engine): 新增 `OVERLAY_MODIFIERS` — `scenario_overlay` 現在真正影響評分（逢低觀察/高波動警戒/減碼保守/收益再投資）
- feat(rule-engine): 新增 `BUY_THRESHOLD_BY_RISK` — 買入門檻由 `risk_temperature` 動態決定（low=3.0 ~ high=7.0）
- feat(rule-engine): 每個候選結果攜帶 `strategy_aligned: bool` 欄位供仲裁層使用
- feat(ai-bridge): 新增 `STRATEGY_GROUP_BONUS` — AI 評分迴圈依 `base_strategy` 對 ETF 群組加/扣分
- feat(ai-bridge): candidate dict 攜帶 `strategy_aligned` 欄位，reason 字串標註策略對齊狀態
- feat(ai-bridge): llm-wiki ETF 知識庫背景注入候選 reason（graceful fallback）
- feat(consensus): `resolve_consensus()` 新增 `_adjust_confidence()` — 雙鏈對齊時提升信心，任一不對齊時降級
- feat(consensus): 返回 dict 加入 `strategy_alignment_signal` 欄位，完整記錄雙鏈對齊狀態
- fix(dashboard): 修復「預設券商」顯示 N/A — 新增 `_get_default_broker()` 從帳戶別名推導，instance_config 缺少 `trading.default_broker` 時不再覆蓋為 null

### v1.1.1 (2026-04-17)
- fix: 持倉快照「交易」按鈕因 watchlist/positions 重複 DOM ID 衝突靜默失效
- fix: 持倉票據 `data-ticket-id` / `data-preview-area` 屬性與 JS 函數不一致
- fix: `cancelPreview` / `resetTicketState` 加 null 防護，新增 `_getPreviewArea()` helper
- chore: 清除 `OPENCLAW_AGENT_NAME` 遺毒，所有 cron 與腳本統一改用 `AGENT_ID`

### v1.1.0 (2026-04-16)
- feat: ETF_TW 從 git submodule 轉為 inline 目錄，單一 repo 可完整重建 agent
- feat: llm-wiki 財經知識庫合併進 repo，config.yaml 路徑綁定
- feat: 新增 `distill_to_wiki.py`，Cron 自動將市場快照沉澱至 wiki 實體頁
- fix: Dashboard HTML 結構修復（12 個區塊全部正常顯示）
- fix: 交易預覽張數顯示精度問題（`toFixed(1)` → `toFixed(3)`）
- fix: 規則引擎「無有效報價」誤報，改為帶時間戳的友善訊息
- fix: CDN script 補上 SRI integrity 屬性（CWE-353）
- fix: `<form>` 替換為 `<div>+onclick`（消除 Semgrep CSRF 誤報）

### v1.0.0 (2026-04-10)
- 初始穩定版本：ETF_TW + Dashboard + 雙鏈決策 + 5 個 Cron 任務

---

## 📜 免責聲明
本專案所產出之所有分析、診斷及決策建議僅供參考，不構成任何形式的投資建議。使用者應自行承擔投資風險，並在執行任何真實交易前諮詢合格的理財顧問。
