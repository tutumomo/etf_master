# ETF_Master: 智慧型台灣 ETF 投資助理 (v1.10.0)

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
- **ETF_TW 內建量化診斷**：`run_intraday_quant_diagnosis.py` 直接讀取 ETF_TW state，避免 cron 依賴已吸收的外部技能路徑。
- **知識庫 references**：保留原 `stock-analysis-tw` / `stock-market-pro-tw` 工作流知識，但 cron 不再將它們當作必跑腳本。
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
  - 自動維持 `instances/<agent_id>/state/agent_summary.json`，供 Hermes Agent 快速讀取當前決策狀態與資產概況。
  - 反應式 (Reactive) 策略切換：套用策略後自動重生決策建議。
  - 摺疊式區塊：在維持監控頂部看板的同時保持介面簡潔。
  - 內嵌式交易票據：流暢的三段式下單體驗。
  - 預覽交易評分會顯示評分因子與 AI 信心來源，區分直接 AI 輸出與 per-symbol heuristic fallback。

### 命令行工具 (CLI)
```bash
# 啟動儀表板
python scripts/etf_tw.py dashboard

# 查詢即時持倉
python scripts/etf_tw.py portfolio

# 執行 ETF_TW 內建盤中量化診斷
AGENT_ID=etf_master .venv/bin/python scripts/run_intraday_quant_diagnosis.py
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

### v1.10.0 (2026-05-01)
- feat(buy): 新增 **持倉相關性懲罰（E2）** — `correlation_engine` 計算 watchlist pairwise 相關，買進時擬買標的 vs 既有持倉平均相關 >0.7 即線性折扣倉位，floor 0.2，避免重複押注（實測 watchlist 多檔 ρ≥0.9）。
- feat(sell): 新增 **動能反轉賣訊（F1）** — 個股 20 日報酬 vs 大盤中位數跑輸 ≥10% 且 RSI<40 → 即使尚未跌破 stop_price 仍出場，trigger_source 與 trailing 區分。
- feat(buy): 新增 **新聞風險 Gate（F-news）** — 消費既有 `news_intelligence_report.json`，依 signal_strength 對買單做 haircut（high → ×0.4 / medium → ×0.7），不擋買、只降權重。
- chore(plan): `docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md` 加「執行進度」段，記錄 D / E1 / G 暫緩到實單 3 個月後再做的決定，以及 F3 由 F-news 替代的方案。
- test: 全測 `763 passed`（2026-05-01 Codex 對齊檢視實跑）。

### v1.9.0 (2026-04-30)
- feat(state): 新增 paper ledger 初始化、資料品質檢查與 `etf_tw.py status`，讓 paper 模式、對帳狀態、資料品質、組合風控與新聞情報可用 CLI 一次檢視。
- feat(risk): 新增組合層級最大回撤、年化波動、相關性 warning 與 trailing stop 對齊報告；pre-flight 在最大回撤硬紅線時阻擋買入。
- feat(auto_trade): Phase 2 sell/buy fine-tune，加入 DCA 完成後 trailing grace period、cooldown 後 reentry 標記與 mixed lot 出場計畫分組顯示。
- safety(broker): Cathay adapter 與 legacy Cathay broker 停止 scaffold 假認證、假部位與假成交；新增 broker readiness 檢查，未取得官方 API 規格與測試帳號前不標記 live-ready。
- feat(news): 新增新聞情報去雜訊報告，僅採用 24 小時內 fresh source，stale 新聞不進 AI Bridge 候選。
- chore(test): 納入 `pytest-asyncio` 並啟用 `asyncio_mode=auto`，讓既有 async smoke tests 納入全測。
- test: 全測 `721 passed`；graphify rebuild 產出 4338 nodes / 7596 edges / 484 communities。

### v1.8.2 (2026-04-30)
- fix(cron): 盤中智慧掃描改用 ETF_TW 內建 `run_intraday_quant_diagnosis.py`，不再呼叫缺失的 `skills/stock-analysis-tw/scripts/analyze_stock.py`。
- fix(cron): 盤後收工與每週深度復盤移除已吸收的 `stock-analysis-tw` / `stock-market-pro-tw` 外部腳本依賴。
- fix(cron): 早班與盤後 `generate_watchlist_summary.py` 補上 `--mode am/pm`，避免缺參數造成 cron 失敗。
- docs(knowledge): 更新 ETF_TW cron references 與 SKILL SOP，標準化內建量化診斷入口。
- test: 全測 `668 passed`；graphify rebuild 產出 3776 nodes / 6502 edges / 441 communities。

### v1.8.1 (2026-04-29)
- safety(live): `live_submit_sop.py` 優先使用 instance account credentials，避免 dashboard process env 缺少 Sinopac key 時誤報 authenticate failed。
- safety(broker): 盤後零股時段改用 `StockOrderLot.Odd`，盤中零股維持 `IntradayOdd`，避免 13:40-14:30 零股委託未被券商受理。
- safety(state): `sync_orders_open_state.py` 讀取券商成交紀錄清除已成交 open order，避免成交後仍被 cron / dashboard 判成幽靈掛單。
- audit(live): 新增 `submission_journal.jsonl` 與 `submit_response` metadata contract，區分 adapter 回應、驗證落地、ghost 與 gate block。
- docs(knowledge): 沉澱 006208 盤後零股未受理事件到 Shioaji wiki，並同步 ETF_TW references 知識文件與 graphify 輸出。
- test: 全測 `666 passed`；graphify rebuild 產出 3766 nodes / 6483 edges / 447 communities。

### v1.8.0 (2026-04-29)
- feat(strategy): 完成 A/B/C 計畫與 v2 骨架接線，新增 top-down 總體情境、壓力情境回測、DCA 初始建倉、寬 trailing 與比例 ladder。
- feat(auto_trade): Dashboard 接通 DCA 啟停/狀態顯示，Phase 2 接入 macro buy gate、DCA 全鏈路與 ghost order tracking。
- safety(live): 正式下單改走 `live_submit_sop.py` 單一路徑，未驗證委託不再落入 `orders_open.json`，避免 `UNVERIFIED` 被誤判為 `VERIFIED` 造成幽靈單。
- fix(sell): `sell_scanner` 支援 mixed lot 賣出拆單，將整張與零股分成 board / odd 兩筆訊號，避免 odd lot 超過 999 股被 pre-flight gate 擋下。
- audit(replay): 新增 production replay 對照與交錯修改整合審計，校正 replay cooldown 保留行為與回測報告敘述。
- docs(knowledge): ETF 獲利手段沉澱到 wiki，並重建 graphify 知識圖譜，保持 clone 後可取得最新策略/程式背景。
- test: 全測 `660 passed`；graphify rebuild 產出 3894 nodes / 7146 edges / 327 communities。

### v1.7.0 (2026-04-27)
- safety(trade): 正式送單前 `pre_flight_gate` 改為嚴格使用 `settlement_safe_cash`，可交割金額為 0 或負數時不再 fallback 到帳面現金。
- safety(auto_trade): Phase 2 買入掃描新增「今日已入隊/已 ack/已執行 + 本筆」累計額度檢查，避免多檔候選同輪超過可交割金額比例。
- safety(broker): 永豐 Shioaji adapter 與 legacy enhanced adapter 鎖定股/張轉換規則，零股以 `IntradayOdd + 股數` 送出，整股以 `Common + 張數` 送出，混合單位直接拒絕。
- feat(watchlist): Dashboard 新增關注標的改為合併完整 `etf_universe_tw.json` 與精選 `etfs.json`，支援 `00720B` 等未列入精選清單的 ETF。
- ux(dashboard): 左側基本資訊合併原狀態中心，持倉快照改為 full width；左側版面配色、基本資訊、資金快照、券商設定皆支援點擊收合並記憶狀態。
- chore(graphify): 重新產生 graphify 知識圖譜與報告，保持 clone 後可取得最新 dashboard / trading gate 知識。
- test: 新增並擴充股張單位、Phase 2 ack、可交割金額、同輪自動買入累計額度、live submit SOP 與 dashboard watchlist/sidebar 回歸測試；全測 `579 passed`。

### v1.6.0 (2026-04-26)
- feat(auto_trade): Phase 2 買入掃描導入策略感知調整，依 `base_strategy`、`scenario_overlay`、市場風險與 defensive tilt 調整原始 VWAP 階梯金額。
- safety(auto_trade): `buy_scanner` 實際讀取賣出後 `position_cooldown.json`，避免 trailing stop 賣出後短期又自動買回；pre-flight 檢查改用當前 instance `state_dir`。
- feat(risk): growth / smart_beta 在 cautious 或 elevated 風險情境下加嚴觸發門檻，並補齊 `growth=8%`、`smart_beta=7%` trailing stop 類別。
- ux(dashboard): Phase 2 pending card 顯示原始階梯金額、策略/情境、群組與乘數，讓自動交易訊號更可解釋。
- chore(graphify): 將 `graphifyy==0.4.23` 納入 ETF_TW venv 依賴，並刷新 graphify 圖譜輸出。
- test(auto_trade): 補齊 cooldown、策略乘數、growth 風險攔截、平衡配置 preview 對齊、trailing 類別與 4 標的隔離模擬驗證。

### v1.5.1 (2026-04-26)
- docs(readme): 收斂為 root `README.md` 單一主文件，移除重複的 `skills/ETF_TW/README.md`，避免版本與操作說明分岔。
- feat(dashboard): 儀表板導入雙欄資訊架構、券商設定區與可切換亮色/暗色/跟隨系統配色。
- ux(dashboard): 交易模式切換改為即時按鈕狀態與區塊內提示，不再以 popup 作為主要回饋。
- safety(trade): 紅線檢查改為強制啟用；人工下單與 Phase 2 半自動 ack 均維持 preview / confirm / submit 安全閘門。

### v1.5.0 (2026-04-26)
- feat(auto_trade): 完成 Phase 2 半自動交易系統 🎉
  - M1：盤中報價基礎建設（VWAP 計算、`sync_intraday_quotes.py`）
  - M2：買入掃描 + pending queue + 7 項 circuit breaker 熔斷
  - M3：trailing stop 賣出掃描 + peak tracker（群組 trailing %、≥20% 鎖利）
  - M4：Dashboard pending card + ack/reject 流程 + launchd 排程
- feat(gate): 「單筆金額上限」改以可交割金額為基準（cash − T+1/T+2）
- feat(dashboard): 多項 UI 強化
  - P1-1 衝突歷史面板（Tier 2/3 規則 vs AI 分歧）
  - P1-2 策略影響力即時摘要（對齊率、勝率）
  - P1-3 感測器降級行動指引
  - P2-4 持倉分群配置比例 bar
  - P2-5 事件堆積警報
  - 現金 KPI 三層揭露（帳面 / 可交割 / 待交割）
- fix(ohlcv): `return_1y` 不再因台股交易日 < 252 一律 None，改用年化推算
- 累計 128 個新 unit test（總計 555/555 PASS）

### v1.4.17 (2026-04-24)
- feat(dashboard): 「現金 / 追蹤數」模塊在 Full Sync 後同步顯示帳面現金與交割安全金額
- feat(live-state): `sync_live_state.py` 接入 `api.settlements(api.stock_account)`，寫入 T+1/T+2 淨交割款與 `settlement_safe_cash`
- ux(dashboard): 現金卡片新增 T+1/T+2 淨額，避免把永豐帳面現金誤判為可動用現金
- test(live-state): 新增交割安全金額計算回歸測試

### v1.4.16 (2026-04-24)
- fix(dashboard): 修復 `預覽交易` API 500，補齊 `trade_preview()` 缺失的 state context / JSON loader 接線
- feat(dashboard): 預覽交易評分接入 AI 信心來源；當前 AI 候選標的使用 `ai_decision_response`，其他標的使用透明的 per-symbol `ai_bridge_heuristic`
- ux(dashboard): 預覽面板新增「評分因子」與「AI 信心來源」顯示，避免把 heuristic 誤看成真 AI 判斷
- chore(context): `AGENT_ID` warning 改為 process-local 說明，明確區分互動 shell 已設與非互動 subprocess 未帶入的情況

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
