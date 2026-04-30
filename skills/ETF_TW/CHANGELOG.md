# CHANGELOG

## v1.9.0 — 2026-04-30

### Added
- **Paper ledger 初始化**：新增 `scripts/init_paper_ledger.py` 與 CLI `paper-init`，可用 `SYMBOL,QUANTITY,PRICE,DATE` 建立 paper 初始持倉並同步 state。
- **資料品質報告**：新增 `scripts/data_quality.py`，檢查 `market_cache` 新鮮度、缺報價、positions / snapshot / open orders 對齊狀態。
- **組合風控報告**：新增 `scripts/portfolio_risk_report.py`，計算最大回撤、年化波動、標的相關性與 trailing stop 對齊狀態。
- **Broker readiness**：新增 `scripts/broker_readiness.py`，明確列出 Cathay 等 broker 進入 live-ready 前缺少的官方規格、測試帳號與 mapping 驗證。
- **新聞情報去雜訊報告**：新增 `scripts/news_intelligence_report.py`，整合既有 `news_articles` / `news_headlines` / RSS cache，僅採用 24 小時內 fresh source 產生強弱訊號。
- **CLI 狀態摘要**：`etf_tw.py status` 現在一次顯示模式、帳務、持倉、成交對帳、資料品質、組合風控與新聞情報。

### Changed
- **Phase 2 策略 fine-tune**：`sell_scanner` 加入 DCA 完成後 trailing grace period 與 mixed lot 出場計畫 metadata；`buy_scanner` 標記 cooldown 後 reentry，不繞過既有風控。
- **Dashboard pending 顯示**：Phase 2 mixed lot 出場訊號在 dashboard 以同一出場計畫分組呈現，避免整張 / 零股拆單被誤讀為重複下單。
- **報表模板標準化**：早班、盤後與週報輸出改用 `report_templates.py` 標準章節，並新增 cron 舊腳本缺口檢查。
- **Agent summary 擴充**：`sync_agent_summary.py` 納入 filled reconciliation、decision quality、data quality、portfolio risk 與 news intelligence 摘要。
- **Async 測試環境**：`pytest-asyncio>=1.3.0` 納入 requirements，`pytest.ini` 啟用 `asyncio_mode=auto`，讓 async smoke tests 納入全測。

### Fixed
- **成交對帳閉環**：callback / polling 對 terminal `filled`、`partial_filled` 狀態同步 fills ledger，`filled_quantity` 缺失時回退使用原委託數量。
- **Cathay 假功能移除**：`cathay_adapter.py` 與 legacy `cathay_broker.py` 不再假認證、假回傳部位或假成交；未整合官方 API 前所有 submit 皆拒絕。
- **新聞 stale 防呆**：新聞情報報告忽略 24 小時以上 stale source，並修正無 timezone timestamp 導致 freshness 為負數的問題。
- **`.gitignore` 誤傷修復**：移除大小寫不敏感檔案系統上會誤忽略 `skills/ETF_TW` 新檔的 `skills/etf_tw/` 規則，並忽略本機新聞 / preview cache。

### Tests
- **全測驗證**：`721 passed`。
- **Graphify 同步**：重建 graphify code graph，產出 4338 nodes / 7596 edges / 484 communities。

## v1.8.2 — 2026-04-30

### Added
- **ETF_TW 內建盤中量化診斷**：新增 `scripts/run_intraday_quant_diagnosis.py`，直接從 `market_cache.json`、`watchlist.json`、`positions.json` 與 `intraday_tape_context.json` 產生 `intraday_quant_diagnosis.json`。

### Changed
- **盤中智慧掃描 cron**：`cron/jobs.json` 改用 ETF_TW 內建量化診斷，不再呼叫缺失的 `skills/stock-analysis-tw/scripts/analyze_stock.py`。
- **盤後 / 週復盤 cron**：移除已吸收外部技能 `stock-analysis-tw` / `stock-market-pro-tw` 的必跑路徑，改以 ETF_TW state 與內建診斷生成報告素材。
- **Cron SOP 文件**：更新 intraday、post-market、weekly review references 與 `SKILL.md`，把 `run_intraday_quant_diagnosis.py` 列為標準入口。

### Fixed
- **watchlist summary 缺參數**：早班 / 盤後 cron 對 `generate_watchlist_summary.py` 補上 `--mode am/pm`。
- **缺失腳本缺口回報**：消除盤中報告「stock-analysis-tw 腳本不存在」缺口。

### Tests
- **全測驗證**：`668 passed`。
- **Graphify 同步**：重建 graphify code graph，產出 3776 nodes / 6502 edges / 441 communities。

## v1.8.1 — 2026-04-29

### Added
- **Submission journal**：新增 `scripts/submission_journal.py`，讓 live submit SOP 將 gate block、adapter submit response、submit verification 與 ghost 結果寫入 `submission_journal.jsonl`。
- **Submit response contract**：`submit_response` 正式納入 broker reconciliation metadata contract，明確標示 `verified=false`、`landed=false`，不可單獨寫入 `orders_open.json`。
- **盤後零股事故 wiki**：新增 2026-04-29 006208 盤後零股未受理事件紀錄，沉澱永豐網站查無委託與系統 ghost 驗證一致的處理規則。

### Changed
- **Live submit credentials**：`live_submit_sop.py` 優先從 instance `AccountManager` 建立 broker adapter，env vars 僅作 fallback，避免 dashboard 正式下單因 process env 缺 key 失敗。
- **Orders open lifecycle**：`sync_orders_open_state.py` 在 live-ready mode 讀取券商成交紀錄，將已成交的本地 open order 轉為 terminal 並清除。
- **ETF_TW references 同步**：納入 ETF_TW references 知識文件索引，讓 clone 後可取得 cron、reconciliation、worldmonitor、wiki pipeline 等補充知識。

### Fixed
- **盤後零股 order_lot**：Sinopac adapter 在 13:40-14:30 改用 `StockOrderLot.Odd`，盤中零股維持 `StockOrderLot.IntradayOdd`。
- **成交後 ghost 誤報**：已成交委託不再長期殘留於 `orders_open.json`，降低 cron 巡檢誤報幽靈單的機率。

### Tests
- **全測驗證**：`666 passed`。
- **Graphify 同步**：重建 graphify code graph，產出 3766 nodes / 6483 edges / 447 communities。

## v1.8.0 — 2026-04-29

### Added
- **A/B/C 策略驗證鏈**：加入 top-down macro regime、壓力情境回測與 production replay，讓 simulator 與生產 scanner 行為能被對照。
- **v2 自動交易骨架**：接入 DCA 初始建倉、寬 trailing、比例 ladder、macro buy gate 與 Phase 2 DCA dashboard 啟停/狀態 API。
- **交錯修改整合審計**：新增 `docs/intelligence-roadmap/2026-04-29-interleaved-change-audit.md`，記錄 Codex / Claude-code 交錯修改後的風險邊界、修正與待辦。
- **ETF 獲利手段 wiki**：將 DCA、配置再平衡、折溢價、配息、趨勢與風控出場等知識沉澱到 wiki。

### Changed
- **Live submit 單一路徑**：Dashboard 與 Phase 2 ack 的正式送單改走 `scripts/live_submit_sop.py`，未驗證回報進 ghost log，不落入 `orders_open.json`。
- **Production replay cooldown 保留**：replay 不再每日清空 `position_cooldown.json`，使回放結果更接近真實 ack 後的生產狀態。
- **Replay 報告校正**：修正過度樂觀敘述，明確標示 production 在 2024 Bull 多頭報酬落後 simulator / BAH，但回撤控制有效。

### Fixed
- **Ghost order 誤判**：修正 `"VERIFIED" in stdout` 會把 `UNVERIFIED` 誤判為已驗證的問題，避免永豐查不到的正式委託被寫成 open order。
- **Mixed lot trailing sell**：`sell_scanner` 現在會把 15,763 股這類混合部位拆成 15,000 股 board 與 763 股 odd，避免 odd lot 超量被 pre-flight gate 擋下。

### Tests
- **全測驗證**：`660 passed`。
- **Graphify 同步**：重建 graphify code graph，產出 3894 nodes / 7146 edges / 327 communities。

## v1.7.0 — 2026-04-27

### Added
- **股/張單位安全回歸測試**：新增 `tests/test_sinopac_unit_safety.py`，鎖定 50 股零股不可被送成 1 張、2000 股整股需送成 2 張、1500 股混合單位必須拒絕。
- **完整 ETF universe watchlist 支援**：Dashboard 新增關注標的時合併 `data/etf_universe_tw.json` 與精選 `data/etfs.json`，讓 `00720B` 等債券 ETF 可被正常加入與分組。
- **同輪自動買入累計額度檢查**：`buy_scanner.py` 在每筆候選入隊前檢查今日 pending/acked/executed 金額加上本筆是否超過 `settlement_safe_cash × max_buy_amount_pct`。
- **左側欄收合互動**：左側版面配色、基本資訊、資金快照、券商設定接入既有 `toggleCard()` 與 localStorage 狀態記憶。

### Changed
- **可交割金額成為硬基準**：`pre_flight_gate.py` 只要收到 `settlement_safe_cash` 就以它為 sizing base；即使為 0 或負數也不再 fallback 到帳面現金。
- **Live Submit SOP gate context 補齊**：`live_submit_sop.py` 送 pre-flight 時帶入 account snapshot、positions inventory、safety redlines 與 state_dir，避免未來免人工確認入口繞過紅線設定。
- **Dashboard 資訊架構收斂**：原右側「狀態中心」合併進左側「基本資訊」，「持倉快照」改為 full width，降低重複資訊並提升持倉表可讀性。

### Fixed
- **Legacy enhanced adapter 零股風險**：修正 `sinopac_adapter_enhanced.py` 原本 `quantity < 1000` 會送 `quantity=1` 且未指定 `order_lot` 的危險邏輯。
- **當前 Sinopac adapter 底層防線**：`sinopac_adapter.py` 在 `_submit_order_impl` 也拒絕 1000 以上但非整張的混合單位，避免直接呼叫底層方法繞過 pre-flight。

### Tests
- **全測驗證**：`579 passed`。
- **Graphify 同步**：重建 graphify code graph，產出 3561 nodes / 6567 edges / 233 communities。

## v1.6.0 — 2026-04-26

### Added
- **Phase 2 策略感知買入**：`buy_scanner.py` 在 VWAP 跌幅階梯後套用 `base_strategy`、`scenario_overlay`、`risk_temperature` 與 `defensive_tilt` 乘數，讓自動買入不再只是固定跌幅觸發。
- **Phase 2 訊號可解釋化**：pending card 顯示原始階梯金額、調整後金額、策略/情境、群組與乘數，方便人工 ack 前判斷訊號來源。
- **growth / smart_beta trailing stop**：`peak_tracker.py` 新增 growth 8%、smart_beta 7% 類別，避免 fallback 成 core 6%。
- **graphify venv 依賴**：`graphifyy==0.4.23` 納入 ETF_TW requirements，讓 repo 規範的 graphify rebuild 可用 `.venv/bin/python3` 執行。

### Changed
- **賣出後 cooldown 真正生效**：`buy_scanner.py` 現在會讀 `position_cooldown.json`，賣出冷卻期間不再自動買回同一檔。
- **平衡配置 preview 對齊修正**：Dashboard preview 將 core / income / defensive 都視為平衡配置可對齊群組，不再只認 core。
- **Instance state 對齊**：Phase 2 買入 pre-flight gate 現在傳入當前 `state_dir`，避免測試或多 instance 場景誤讀全域紅線。
- **VWAP 階梯邊界修正**：修正剛好 -3.00% 可能因浮點誤差落到較低階梯的問題。

### Tests
- **策略感知買入回歸**：新增 cooldown、策略/overlay 金額調整、cautious/elevated growth 攔截與 ladder 浮點邊界測試。
- **隔離模擬**：使用臨時 state 跑 2 個持倉賣出、2 個關注買入掃描；`0050`/`00878` 賣出入 pending，`00679B` 買入入 pending，`00830` 依 growth 風險門檻被策略攔截。
- **驗證**：核心測試集 569 passed；graphify rebuild 成功產出 3498 nodes / 6456 edges / 213 communities。

## v1.5.1 — 2026-04-26

### Added
- **Dashboard 雙欄與設定區**：主畫面加入左側資訊/設定欄，支援券商設定與亮色、暗色、跟隨系統配色切換。
- **正式下單安全確認**：人工下單延伸為 preview id + 精確確認字串 + submit 的流程，並保留 live mode、交易時段與紅線檢查。

### Changed
- **README 單一來源**：root `README.md` 成為唯一主 README，移除重複的 `skills/ETF_TW/README.md`，避免 GitHub 版本與技能目錄文件分岔。
- **交易模式切換回饋**：Dashboard 的 Live/Paper 切換改為即時按鈕狀態與區塊內提示，不再用 popup 承擔主要確認。
- **紅線檢查強制啟用**：移除可關閉紅線檢查的假開關，後端與 pre-flight gate 均固定執行紅線檢查。

### Tests
- **Dashboard / trading gate 回歸**：補齊正式送單、每日送單次數、Phase 2 ack submit gate、紅線強制啟用與基礎模板測試。

## v1.4.17 — 2026-04-24

### Added
- **Dashboard 現金/交割安全金額同步顯示**：`sync_live_state.py` 在 live-ready Full Sync 時一併查詢 `api.settlements(api.stock_account)`，寫入 T+1/T+2 淨交割款與 `settlement_safe_cash`，讓「現金 / 追蹤數」卡片同時顯示帳面現金與交割安全金額。

### Changed
- **現金卡片透明化**：`overview.html` 顯示「交割安全」與 T+1/T+2 淨額，避免只看帳面現金誤判可動用金額。

### Tests
- **回歸測試**：`tests/test_sync_live_state.py` 新增交割安全金額計算測試，覆蓋 T+1/T+2 淨額與負數安全金額 floor 顯示值。

## v1.4.16 — 2026-04-24

### Fixed
- **Preview API 500 修復**：`dashboard/app.py` 的 `trade_preview()` 補齊 `context.get_state_dir()` 與 `safe_load_json` 接線，修復預覽交易路徑會因 `NameError` 直接炸成 `500 Internal Server Error` 的問題。
- **投資評分鏈路恢復有效**：`watchlist.json` 同時支援 `watchlist` / `items` 結構，`market_regime` 改為支援 `balanced_bullish` / `*_cautious` 這類複合值，不再讓策略對齊與市場 regime 因子靜默失效。

### Added
- **Preview 評分接入 AI 信心來源**：`trade_preview()` 現在會先使用 `ai_decision_response.json` 的真 AI 信心；若當前標的不是 AI 候選，則退回 per-symbol `ai_bridge_heuristic`，讓所有 preview 標的都有可追溯的信心來源。
- **Preview 面板透明化**：`overview.html` 新增「評分因子」與「AI 信心來源」顯示，清楚區分真 AI 與 heuristic。
- **回歸測試**：新增 `tests/test_dashboard_trade_preview.py`，覆蓋 preview payload、watchlist `items` 相容、AI 信心直接來源與 heuristic fallback。

### Changed
- **Heuristic AI 信心改保守**：per-symbol fallback 對過熱 RSI 採扣分處理，提升 `high` 門檻，避免把過熱標的輕易顯示成高信心。
- **AGENT_ID warning 文案修正**：`scripts/etf_core/context.py` 現在明確說明缺的是「current process env」，避免把非互動 subprocess 的 env 缺失誤解成整台機器未設定。

## v1.4.15 — 2026-04-24

### Added
- **Codex graphify hook 接線完成**：新增 repo-local `AGENTS.md` 與 `.codex/hooks.json`，讓 Codex 在回答程式碼庫問題前先檢查 `graphify-out/GRAPH_REPORT.md` / `graphify-out/graph.json`，並在程式碼變更後保留圖譜更新入口。

### Changed
- **知識工作流收斂**：將 `graphify` 的圖譜探索與 `llm-wiki` 的長期沉澱角色在專案層文件中明確區分，避免後續代理把兩者混成同一條流程。

### Docs
- **README 對齊知識工作流**：更新 root `README.md` 與 `skills/ETF_TW/README.md`，明確區分 `graphify` 的圖譜探索角色與 `llm-wiki` 的長期知識沉澱角色。

## v1.4.14 — 2026-04-23

### Added
- **`strategy_audit.py`（新腳本）**：稽核 `decision_provenance.jsonl` 中策略影響力的真實程度。計算策略分佈、per-strategy 對齊率、各策略實際選出的 ETF 群組、策略對齊 vs 非對齊勝率對比、策略切換次數、平均評分差異。`format_strategy_audit_section()` 輸出 Markdown 供週報直接嵌入。
- **`generate_decision_quality_weekly.py`（修改）**：`format_weekly_report()` 新增可選 `strategy_audit` 參數，`main()` 自動執行稽核並嵌入「策略影響力稽核」段落至週報末尾。
- **`pre_flight_gate.compute_investment_score()`（新函數）**：對下單候選計算 -10~+10 投資評分（不影響通過/攔截邏輯），因子包含 AI 信心（high/medium/low）、策略對齊、規模比例、交易時段、市場 regime。`check_order()` 通過時自動附加 `investment_score` 與 `score_breakdown`。
- **`dashboard/app.py trade_preview`（修改）**：讀取 `market_context_taiwan.json` 與 `watchlist.json` 以填入 `market_regime` + `strategy_aligned`，回傳 `pre_flight.investment_score` 與 `score_breakdown` 給前端。
- **`dashboard/templates/overview.html`（修改）**：預覽面板新增「投資評分」列，顯示數字 + 顏色 bar（≥6 綠/3–5 黃/≤2 紅）；PASS 時顯示「✓ 已通過所有風險檢查」，BLOCK 時才顯示「攔截原因：」（修正舊版 PASS 時誤顯示「攔截原因：passed」的 bug）。
- **`pre_flight_gate._pass()`（修改）**：`reason` 由 `'passed'` 改為空字串，讓前端 `if (reason)` 判斷乾淨。
- **24 個新測試**：`test_pre_flight_gate.py`（14 tests，覆蓋 _pass reason、compute_investment_score 各因子、check_order 附加評分）、`test_strategy_audit.py`（10 tests，覆蓋分佈統計、對齊率、切換計數、勝率、Markdown 格式）。

## v1.4.13 — 2026-04-22

### Added
- **Dashboard 全鏈路同步先對齊券商持倉**：`dashboard/app.py` 的 `_run_full_pipeline_helper()` 現在把 `sync_live_state.py` 放在 `refresh_monitoring_state.py` 之前，確保後續 monitoring / auto-decision / consensus 都建立在最新券商持倉與資產快照上。
- **台灣 ETF 分析陷阱文件化**：`skills/stock-analysis-tw/SKILL.md` 新增 Taiwan ETF 專屬已知問題章節，集中說明 `dividendRate=None`、`quoteSummary 404`、`.TW/.TWO` suffix 差異與建議 fallback，避免後續代理重踩同一類 yfinance 誤判。

### Changed
- **Dashboard 使用者訊息與刷新節奏對齊真實耗時**：`overview.html` 成功 banner 改為明示「含券商持倉同步」，自動刷新從 5 秒延長至 15 秒，避免使用者在 `sync_live_state.py` 尚未完成時看到半套狀態。
- **Profile runtime config 結構化**：root `config.yaml` 改為 `model.default/provider` 形式，啟用 `memory.provider: builtin`，並同步調整 `display.skin=etf-master`、`dashboard.theme=mono`、`busy_input_mode=queue` 等運行參數。

### Docs
- **Wiki 市場體制與風險頁更新**：`wiki/concepts/market-view.md`、`wiki/concepts/risk-signal.md` 更新為 2026-04-21 早班的 regime / rotation / risk readout，反映收益型延續強勢、核心權值分化與防守型持續落隊。
- **ETF 實體頁快照刷新**：更新 10 檔既有 ETF 實體頁最新價格，並為 `00922-zhaoying-blue-chip-30.md` 新增市場數據快照區塊。

## v1.4.12 — 2026-04-22

### Added — Subsystem D: P6 事件驅動掃描觸發

- **`event_driven_scan_trigger.py`（新腳本）**：讀取 `state/major_event_flag.json`，當 L2/L3 事件 `should_notify=True` 時立即觸發 `run_auto_decision_scan`，無需等待定時 cron（30 分鐘間隔）。純函數 `should_trigger_scan()` 負責去重邏輯（相同 `event_hash` 不重複觸發），並在觸發前更新 `event_review_state.json` 防止 race condition。
- **`run_auto_decision_scan.py`（修改）**：讀取 `major_event_flag.json`，在 `chain_sources` 中新增 `event_triggered: bool` 與 `event_level: str | None`，讓 provenance 記錄清楚標示「例行 cron 掃描」vs「L2/L3 事件驅動掃描」，供事後分析查詢。
- **7 個新測試**：`test_event_driven_scan_trigger.py` 覆蓋 `should_trigger_scan` 純函數的全部分支（no_event、level_too_low、already_notified、already_triggered、L2 trigger、L3 trigger、triggered=False 短路）。

---

## v1.4.11 — 2026-04-22

### Added — Subsystem C: P1 知識迴圈衰減偵測 + P4 LLM 確定性稽核

- **P1 — `_read_learned_rules_freshness()` in `generate_ai_decision_request.py`**：`wiki_context` 新增 `learned_rules_freshness` 欄位（`total_rules / active / tentative / stale / most_recent_update / knowledge_healthy`）。AI Bridge 現在能偵測知識庫是否衰退（所有規則 stale 或庫空）並在決策時調整信心。
- **P4 — `_compute_input_fingerprint()` in `generate_ai_decision_request.py`**：計算 12 字元 SHA256 前綴（市場狀態 + 持倉 + 策略）寫入 `ai_decision_request.json`；`generate_ai_agent_response.py` 將 `input_fingerprint` 帶入 `input_refs`。相同市場輸入的兩次掃描可比對 fingerprint，量化 LLM 非確定性。
- **7 個新測試**：`test_generate_ai_decision_request.py` 新增 freshness 空庫、健康庫、全 stale、fingerprint 穩定性、fingerprint 輸入敏感度、端對端 6 個測試。

---

## v1.4.10 — 2026-04-22

### Added — Subsystem B: P2 衝突溯源 + P5 反事實計量

- **P2 — `chain_sources` 新增衝突欄位**：`conflict_detail`（Tier 2/3 人類可讀原因）與 `ai_bridge_reasoning`（AI Bridge 決策摘要，僅 conflict=True 時填入）寫入 `decision_provenance.jsonl`，事後可查詢 AI 為何反對規則引擎。
- **P5 — `tier2_rule_overruled_ai` 反事實桶**：`sync_decision_reviews.py` 的 `update_chain_breakdown()` 新增此桶，統計規則引擎在 AI 反對下仍執行的決策（Tier 2）勝率，量化 AI 異見是否為真實信號。週報 markdown 同步新增「Tier 2 規則強推」行。
- **8 個新測試**：`test_sync_decision_reviews.py` 新增 conflict_detail 儲存、None 語意、tier2 桶計數、無 tier2 時桶為零 4 個測試。

---

## v1.4.9 — 2026-04-22

### Added — Subsystem A: P3 感測器降級框架

- **`sensor_health.py`（純函數核心）**：`CRITICAL_SENSORS`（portfolio/market_cache/market_context，任一失效管線中止）、`AUXILIARY_SENSORS`（event_context/tape_context/worldmonitor/central_bank_calendar，失效降級繼續），回傳 `SensorHealthResult` dataclass。
- **`check_sensor_health.py`（CLI 診斷腳本）**：獨立執行，讀 `state/sensor_health.json` 輸出人類可讀報告，exit code 永遠 0（不影響生產）。
- **`run_auto_decision_scan.py`（接入）**：關鍵感測器失效時寫 `lock_reason` + 輸出 `AUTO_DECISION_SCAN_CRITICAL_SENSOR_FAIL:*` + return 1；輔助感測器缺失時在 `context_summary` 前綴 `[資料不完整: ...]`，繼續執行。
- **`state/sensor_health.json`**：每次掃描自動產生，try/except 防止寫入失敗阻斷管線。
- **7 個新測試**：全部通過（happy path + 6 negative paths）。

---

## v1.4.6 — 2026-04-20

### Added
- **決策自動復盤管線（Auto Decision Review Pipeline）**：完全自動化 T+N 價格回填 → verdict 判定 → 雙鏈統計 → 週報寫入 wiki 的整個循環，消除手動標記 `reviewed`/`superseded` 步驟。
  - `sync_decision_reviews.py`：每天 15:05 盤後掃描到期 T1/T3/T10 窗口，自動填入 verdict（±1.5% 門檻），三窗口填滿後自動寫入 `outcome_final`。
  - `generate_decision_quality_weekly.py`：每週六 09:05 產出 `wiki/decision-weekly-YYYY-WNN.md` 與 `wiki/decision-quality-latest.md`。
  - `provenance_logger.py`：`build_provenance_record()` 新增 `chain_sources` 參數，記錄雙鏈仲裁來源（rule_engine/ai_bridge/tier）。
  - `run_auto_decision_scan.py`：將 `consensus` dict 扁平化為 `chain_sources_payload` 傳入 provenance。
  - `decision_quality_report.json` 新增 `chain_breakdown` 區塊（rule_engine/ai_bridge/tier1_consensus/unknown_source 四桶勝率）。
- **Cron 新增 2 個 job**：`ETF 決策自動復盤`（15:05 平日）、`ETF 決策品質週報`（09:05 週六）。Job 數量 7→9。
- **verify_deployment.sh**：cron 門檻從 ≥7 更新為 ≥9。

### Fixed
- **AI 推理管線修復**：`refresh_decision_engine_state.py` 的 SCRIPTS 清單缺少 `generate_ai_agent_response.py`，導致 worldmonitor 信號「進 request、沒進推理」。修法：在 `run_auto_decision_scan.py` 之後加入該腳本，確保 `risk_context_summary` 正確生成。
- **00679B yfinance 404 修復**：新增 `symbol_mappings.json` 的 `00679B` 條目，指定 `.TWO` 後綴，跳過 `.TW` 404。
- **Cron wrapper 腳本**：新增 `scripts/sync_decision_reviews.py` 和 `scripts/generate_decision_quality_weekly.py` wrapper，修正 Hermes cron `script` 欄位從 `HERMES_HOME/scripts/` 解析的問題。
- **WIKI_DIR 路徑修復**：`generate_decision_quality_weekly.py` 的 `WIKI_DIR` 從 `parents[2]` 修正為 `parents[3]`，指向正確的 `profile/wiki/`。

### Validation
- 15 新增測試全通：`test_sync_decision_reviews.py`（10 tests）、`test_generate_decision_quality_weekly.py`（5 tests）
- 全套 364 tests passed，4 個既有失敗不變
- 4 個 cron wrapper 即時觸發全通過（worldmonitor daily/watch、decision review、weekly report）
- `risk_context_summary` 驗證：包含 worldmonitor 信號，不再為空字串
- `00679B` yfinance 驗證：成功取得 `26.91` 報價，source=`yfinance:00679B.TWO`

## v1.4.5 — 2026-04-19

### Added
- **Wiki 投資策略知識注入決策鏈**：`generate_ai_decision_request.py` 新增 `wiki_context.investment_strategies` 與 `wiki_context.undervalued_ranking`，使 dashboard 建議決策能引用「投資策略十大實務」與「ETF 低估排行」知識。
- **Wiki 知識庫新增 4 頁**：`skills/ETF_TW/wiki/investment-strategies.md`（十大策略+5陷阱+0407 Self-Check）、`undervalued-etf-ranking.md`（TOP10 低估排行）、`market-view.md`（風險升級）、`risk-signal.md`。
- **P0 修復 market_value=0**：`sync_live_state.py` 在 Shioaji API 回傳 market_value=0 時，改從 positions 計算，total_equity 同步重算。

### Validation
- `generate_ai_decision_request.py` 產出 `wiki_context` 含 4 個非空欄位：`market_view`(1917字元)、`risk_signal`(2329字元)、`investment_strategies`(5184字元)、`undervalued_ranking`(2270字元)。

## v1.4.4 — 2026-04-19

### Fixed
- **Wiki 背景鏈路修補（request 層）**：`generate_ai_decision_request.py` 改為自動解析 profile wiki (`~/.hermes/profiles/etf_master/wiki`) + instance wiki fallback，不再依賴錯誤路徑 `docs/wiki/shioaji`。
- **Wiki 實體檔名對齊**：支援 `{symbol}.md` 與 slug 形式（如 `0050-yuanta-taiwan-50.md`），持倉標的可正確注入 `wiki_context.entities`。
- **Wiki 風險概念注入**：新增 `wiki_context.risk_signal`，與 `market_view` 一起提供給後續推理鏈。
- **智能體推理層接線**：`generate_ai_agent_response.py` 新增 wiki fallback 載入，並把 worldmonitor 指標（供應鏈/地緣/台海/告警）明確併入 `risk_context_summary`，避免「request 有資料、reasoning 沒使用」。

### Validation
- `AGENT_ID=etf_master .venv/bin/python3 scripts/generate_ai_decision_request.py`：`wiki_context.market_view/risk_signal/entities` 皆非空。
- `AGENT_ID=etf_master .venv/bin/python3 scripts/generate_ai_agent_response.py`：`candidate.reason` 出現 Wiki 分類；`reasoning.risk_context_summary` 含 worldmonitor 欄位。
- `pytest tests/test_ai_decision_bridge_contract.py -q`：3 passed
- `pytest tests/test_sync_worldmonitor.py -q`：9 passed

## v1.4.3 — 2026-04-19

### Added
- **GitHub 操作可追溯補強**：新增 `RELEASE_AUDIT.md`，固定記錄 `tag -> commit -> scope -> validation`。
- **Commit scope guard**：新增 `.github/workflows/commit-scope-guard.yml`，當 commit message 為 `docs(...)` 或 `docs:` 時，禁止夾帶非文件路徑。
- **Local hook guard**：新增 `.githooks/commit-msg`（可搭配 `git config core.hooksPath .githooks`）在本機預先阻擋 `docs` 混合 commit。
- **Release tag audit**：新增 `v1.4.0-audit` annotated tag（對齊 `v1.4.0` 指向 commit），提升版本審計可讀性。

## v1.4.2 — 2026-04-19

### Fixed
- **審計口徑對齊（worldmonitor jobs 路徑）**：統一明確為 repo root 的 `cron/jobs.json`；`skills/ETF_TW/cron/jobs.json` 為錯誤路徑，不再使用。
- **審計口徑對齊（commit 性質）**：釐清 `d7ac4c4` 雖採 `docs(v1.4.0)` 命名，但實際為 **文件 + 功能 + 測試 + wiki** 的混合提交（22 files changed），後續審計與回報以實際 diff 為準。

## v1.4.1 — 2026-04-19

### Fixed
- **Preview/Validate/Submit-Preview 風控鏈一致化**：`scripts/etf_tw.py` 的 `preview-account`、`validate-account`、`submit-preview` 全部接入 `evaluate_pre_flight_gate()`，統一使用 live account context（cash/positions）走 `pre_flight_gate.check_order()`。
- **validate-account 真偽差異修補**：不再只看 adapter `validate_order()`；現在 `valid` 需同時滿足 `validate_order && pre_flight_gate.passed`，並輸出 `pre_flight_gate` 詳細阻擋原因。
- **submit-preview 最終檢核補強**：`validation.valid` 併入 gate 結果，若 gate 阻擋會寫入 `validation.errors`，避免「可預覽但風控已拒絕」的假陽性。
- **Bug 2 修復驗證入冊**：確認 `scripts/distill_to_wiki.py --help` 僅顯示說明，不再觸發 wiki 寫入。

### Validation
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py preview-account --account sinopac_01 data/tmp_preview_risk_test.json` → `status=blocked_by_gate`（原因：`outside_trading_hours`，表示已成功走 gate）
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py validate-account --account sinopac_01 data/tmp_preview_risk_test.json` → `valid=false`，含 `pre_flight_gate` 與阻擋理由
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py submit-preview --account sinopac_01 data/tmp_preview_risk_test.json` → `validation.valid=false`，`errors` 含 gate 阻擋訊息
- `AGENT_ID=etf_master .venv/bin/python3 -c "from scripts.pre_flight_gate import check_order; ... force_trading_hours=False ..."` → `reason=exceeds_sizing_limit`, `allowed=169`
- `before/after stat + .venv/bin/python3 scripts/distill_to_wiki.py --help` → wiki mtime 不變（未寫入）
- `AGENT_ID=etf_master .venv/bin/python3 -m pytest tests -q` → **353 passed**

## v1.4.0 — 2026-04-19

### Added
- **worldmonitor 全球風險雷達整合**：新增 `sync_worldmonitor.py`（daily/watch 雙模式）、`worldmonitor_snapshot.json`、`worldmonitor_alerts.jsonl`、dashboard `/api/worldmonitor-status` 與 `/api/worldmonitor/refresh`。
- **AI 決策輸入擴充**：`inputs.worldmonitor_context` 正式納入 `ai_decision_request.json`，作為第 14 個輸入源。

### Fixed
- 修正 `sync_worldmonitor.py` 在 watch 模式 L3 事件觸發時的錯誤路徑（`skills/ETF_TW/skills/ETF_TW/...`），確保 `check_major_event_trigger.py` 能正確被呼叫。
- 修正 worldmonitor 輸入源描述不一致（第 13/14 個輸入源）為「第 14 個輸入源」。
- 修正每日送單配額測試使用硬編碼日期造成的失敗（改為 Asia/Taipei 當日動態日期），恢復全套測試穩定性。

### Validation
- `tests/test_sync_worldmonitor.py`: 9 passed
- `pytest tests/ -q`: 全綠（修復前 3 failed）

### Maintenance
- 測試警告清零：`tests/test_venv_executor.py` 移除 `return bool` 反模式，新增 `pytest.ini` 過濾第三方 `pydantic` 相容性警告，完整測試輸出 0 warnings。

## v1.3.2 — 2026-04-19

### Added
- **Hermes multi-instance 契約落地**：文件全面補齊 `AGENT_ID` 顯式注入規範，將新安裝預設從「依賴 fallback」改為「入口明確指定 instance」。
- **新裝流程補強**：`README.md`、`INSTALL.md`、`BOOT.md` 新增 AGENT_ID 設定與範例，明確標記 `OPENCLAW_AGENT_NAME` 為 legacy fallback。

### Changed
- `scripts/start_dashboard.sh`：啟動時自動注入 `AGENT_ID=${AGENT_ID:-etf_master}`，並同步填入 legacy 變數給舊腳本相容。
- `scripts/etf_core/context.py`：instance 解析改為 `AGENT_ID` 優先、`OPENCLAW_AGENT_NAME` 次之；缺失警告改為可直接執行的修復導引。
- `scripts/sync_news_via_opencli.py` / `scripts/sync_news_from_local.py`：示例與 state 路徑解析改為 AGENT_ID 優先。

### Validation
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py search 0050`：exit code 0，且不再出現 defaulting 警告。
- `.venv/bin/python3 scripts/distill_to_wiki.py --help`：exit code 0（確認既有修復未回歸）。

## v1.2.2 — 2026-04-17

### Added
- **決策品質報告**：新增 `decision_quality_report.json` 生成流程，統計策略對齊率、confidence bucket 分佈、保險絲攔截率與 Tier arbitration 結果。
- **Paper 壓力測試**：新增多輪掃描與幽靈委託檢測流程，產出 `paper_stress_test_report.json`，驗證 paper mode 週期穩定性。
- **決策回測框架**：新增 `backtest_decision_outcomes.py`，從 `ai_decision_outcome.jsonl` 計算 PnL、勝率、最大回撤與 `quality_gate_passed`。
- **Live Submit SOP**：修正永豐金 `ordno` 讀取路徑，新增 `verify_order_landed()` 3 次輪詢 ghost detection，並建立 `live_submit_sop.py` 單一授權下單入口。
- **Dashboard Live 授權閘門**：新增 `/api/live-mode/status`、`/api/live-mode/unlock` 與 overview 解鎖卡片，雙重確認字串與品質閘門在伺服器端強制驗證。
- **Live submit 回歸測試**：新增 7 場景 regression suite，覆蓋 happy path、ghost、gate block、adapter exception、double-submit dedup、live mode lock。

### Validation
- 全套測試：**328 passed, 6 warnings**

## v1.2.1 — 2026-04-17

### Added
- **Phase 6 決策對齊**：Rule Engine 新增 `OVERLAY_MODIFIERS`（情境覆蓋加分/懲罰）、`BUY_THRESHOLD_BY_RISK`（動態買入門檻）、`strategy_aligned` 候選欄位。
- **AI Bridge 策略強化**：`STRATEGY_GROUP_BONUS` 依 `base_strategy` 動態調整 AI 評分，候選結果帶 `strategy_aligned` 旗標。
- **仲裁優化**：`_adjust_confidence()` 雙鏈同向時升級信心等級，任一鏈失對齊時降級；`resolve_consensus()` 回傳 `strategy_alignment_signal`。
- **LLM-Wiki 注入**：AI Bridge 對前 3 名候選自動讀取本地 `llm-wiki/etf/{sym}.md` 知識注入 Prompt。
- **Phase 8 一鍵全同步**：新增 `_run_full_pipeline_helper()` 與 `/api/decision/full-pipeline` 整合端點；Dashboard 加入一鍵同步按鈕，精簡冗餘操作。
- **Phase 9 Safety Redlines**：Dashboard「交易閾值與安全紅線」UI 區塊落地，支援金額/股數/集中度/日虧損/AI 信心全參數設定與持久化；`pre_flight_gate.py` 全面改寫為 fail-fast 優先序架構，7 道檢查點各有 machine-readable reason code。
- **Dashboard 操作按鈕補齊**：規則引擎「立即規則掃描」、AI Bridge「更新背景知識」/「生成 AI 建議」/「重跑決策管線」。
- **預設券商修復**：`_get_default_broker()` 從帳戶別名推導，解決 N/A 顯示問題。
- **全域 Banner 文字補齊**：`overview.html` 加入技術指標缺失與未對齊成交的精確提示文字。

### Fixed
- `test_safety_redlines.py`：修正錯誤 import 路徑、`@patch` 目標、過時 reason code、sizing context 干擾。
- `test_fuse_v1` / `test_trade_validation` / `test_sizing_policy` / `test_ui_flow`：補齊 `_skip_safety_redlines` context flag，解除 state 檔案對測試環境的干擾。
- `test_dashboard_global_banner_*`：補齊 overview.html 精確 banner 字串。

### Validation
- 全套測試：**275 passed, 0 failures**

---

## v1.3.6 — 2026-04-15
### Added
- **真相層級治理 (Truth Level Governance)**：正式定義三層真相分級，取代單一真相源 (SSoT) 概念。
  - Level 1: Live Direct Evidence (券商 API 即時數據)
  - Level 2: Live Unconfirmed (送單成功待驗證)
  - Level 3: Secondary Info / Snapshots (本機狀態快照)
- 更新 `docs/STATE_ARCHITECTURE.md`、`SKILL.md`、`README.md`、`INSTALL.md` 以反映此架構變更。

### Changed
- 移除所有活文件中將本機 state 稱為「唯一真相源」或「SSoT」的說法，統一改稱為「本機狀態快照」或「次級資訊」。

## v1.2.11 — 2026-04-03
### Changed
- `IMPROVEMENT_PLAN_V3.md` 已重整為主線式規劃，將後續工作改寫為：
  - Filled / Positions Reconciliation Close-the-loop
  - TW Market Calendar / Holiday Detection
  - Submit / Verification / Polling / Callback Contract Completion
  - Partial Fill / Fills Ledger / Portfolio Boundary
  - Dashboard / Summary / Docs Consolidation
- `TASKS.md` 已同步加入新版主線結構摘要，避免後續工作仍混在舊版線性項目中。

## v1.2.10 — 2026-04-03
### Changed
- dashboard overview template 現在正式顯示 filled reconciliation 區塊，並加入 OK / PENDING badge 與未對齊提示。

### Validation
- overview template / overview API / dashboard health / refresh hook / 全鏈路測試通過（78 passed）

## v1.2.9 — 2026-04-03
### Added
- 新增 `filled_reconciliation.py` 的正式 report/state IO 能力。
- 新增 `refresh_filled_reconciliation_report.py`，可由 `fills_ledger.json` + `positions.json` 生成 `filled_reconciliation.json`。
- 新增 filled reconciliation 測試：
  - `test_filled_reconciliation_report.py`
  - `test_filled_reconciliation_state_io.py`
  - `test_refresh_filled_reconciliation_report.py`
  - `test_dashboard_filled_reconciliation_health.py`

### Changed
- dashboard health warning 現可承接 filled reconciliation 警訊。
- `BROKER_RECONCILIATION_RULES.md`、`TASKS.md` 已同步 filled reconciliation / refresh hook 進度。

### Validation
- filled reconciliation / refresh hook / dashboard health / 全鏈路測試通過（76 passed）

## v1.2.8 — 2026-04-03
### Added
- 新增 `fills_ledger.py`，提供 fill facts 的最低可用 state helper 與 merge / state IO。
- 新增 fills ledger / partial fill 測試：
  - `test_fills_ledger_contract.py`
  - `test_fills_ledger_merge.py`
  - `test_fills_ledger_state_io.py`
  - `test_orders_open_callback_fills_ledger.py`
  - `test_polling_fills_ledger_sync.py`
  - `test_partial_fill_position_boundary.py`
  - `test_partial_fill_fill_ledger_contract.py`
  - `test_partial_fill_summary_boundary.py`

### Changed
- `orders_open_callback.py` 現在會在 partial fill callback 時同步更新 `fills_ledger.json`。
- `poll_order_status.py` 現在會在 partial fill polling 時同步更新 `fills_ledger.json`。
- `IMPROVEMENT_PLAN_V3.md` / `TASKS.md` 已同步 partial fill 與 fills ledger 進度。

### Validation
- partial fill / fills ledger / callback / polling / dashboard / sync 相關測試通過（67 passed）

## v1.2.7 — 2026-04-03
### Added
- 新增 `docs/BROKER_RECONCILIATION_RULES.md`，正式整理 broker reconciliation 規則：
  - status rank
  - timestamp precedence
  - broker seq precedence
  - source priority
  - partial fill quantity guard
  - metadata contract
- 新增 `test_submit_and_polling_metadata_contract.py`

### Changed
- `complete_trade.py` 新增 `build_submit_order_row()`，submit verification 寫入 `orders_open` 時帶齊 metadata。
- `poll_order_status.py` 新增 `build_polling_order_row()`，polling 寫入 `orders_open` 時帶齊 metadata。
- `IMPROVEMENT_PLAN_V3.md`、`TASKS.md` 已同步 P4-2 進度。

### Validation
- callback / polling / submit / dashboard / sync 相關測試通過（52 passed）

## v1.2.6 — 2026-04-03
### Added
- 新增 partial fill / callback precedence / stale callback 相關 edge-case 測試：
  - `test_partial_fill_edge_cases.py`
  - `test_callback_precedence_edge_cases.py`
  - `test_partial_fill_normalizer_and_stale_guard.py`

### Changed
- `order_lifecycle.py` 正式納入 `partial_filled` 狀態正規化。
- `orders_open_state.py` 新增基礎 precedence guard，避免較舊 `submitted` 狀態覆蓋較新的 partial / terminal 狀態。
- `sinopac_callback_normalizer.py` 現可帶出 `filled_quantity` / `remaining_quantity`。
- `IMPROVEMENT_PLAN_V3.md` 與 `TASKS.md` 已同步 P4 edge cases 進度。

### Validation
- partial fill / precedence / stale guard 與既有 callback / dashboard / health 測試通過（41 passed）

## v1.2.5 — 2026-04-03
### Changed
- 將 `IMPROVEMENT_PLAN_V3.md`、`TASKS.md`、`CHANGELOG.md` 同步到當前實作狀態。
- 明確標記：P1 / P2 / P3 已完成，P4 進入 callback reconciliation 主幹已建立狀態。

### Validation
- 文件同步前，callback / dashboard / intelligence / health 相關測試通過（34 passed）

## v1.2.4 — 2026-04-03
### Added
- 新增 `dashboard_health.py`，將 dashboard health / warnings / stale / intelligence readiness 聚合為單一模型。
- 新增 callback reconciliation helpers：
  - `order_event_bridge.py`
  - `orders_open_callback.py`
  - `sinopac_callback_normalizer.py`
- 新增 callback / polling / reconciliation 測試：
  - `test_sinopac_callback_normalizer.py`
  - `test_sinopac_callback_bridge.py`
  - `test_sinopac_callback_smoke.py`
  - `test_callback_polling_consistency.py`
  - `test_callback_terminal_statuses.py`
  - `test_callback_polling_verification_consistency.py`

### Changed
- `/health` API 現在回傳 reconciliation-aware health payload，不再只是固定 `{ok:true}`。
- `verify_alignment.py` 與 dashboard overview 現在都納入 state reconciliation 診斷。
- Sinopac adapter 認證成功後會預設註冊 state callback bridge，使 callback 可進入 `orders_open` 更新流程。

### Fixed
- 修正 dashboard runtime 對 `state_reconciliation` 的 import path 問題。
- 修正 `market_intelligence` / history feed 空資料導致 RSI/MACD 長時間載入中與 detail chart 404 的問題。

### Validation
- callback / polling / health / dashboard / intelligence 相關測試通過
- 當前相關測試最高累計：68 passed

## v1.2.3 — 2026-04-02
### Added
- 新增 `docs/IMPROVEMENT_PLAN_V3.md`，正式整理 live lifecycle 下一階段改造方向。
- 新增 dashboard refresh regression test，覆蓋 `/api/refresh` 成功/失敗回應契約。
- 新增 lifecycle regression tests：
  - `test_order_status_contracts.py`
  - `test_orders_open_contract.py`
  - `test_orders_open_position_boundary.py`
  - `test_submit_verification_contract.py`
  - `test_order_lifecycle_helper.py`
  - `test_poll_order_status_contract.py`

### Changed
- `complete_trade.py` 與 `poll_order_status.py` 已接入共用 `order_lifecycle.py`，統一 landed / terminal / status normalization 語意。
- dashboard `/api/refresh` 改為明確回傳 subprocess 結果，只在真失敗時回 500。

### Fixed
- 修正 5050 dashboard 仍跑舊版進程時，UI 顯示 refresh 失敗但主鏈實際已成功的問題。
- 修正 polling flow 對 `failed` / `rejected` / terminal status 的判定分散問題。

### Validation
- dashboard refresh API 測試：通過
- lifecycle / orders_open / submit verification / polling contract 測試：通過
- regression tests 累計：41 passed

## v1.2.2 — 2026-04-02
### Added
- 新增 `docs/STATE_ARCHITECTURE.md`，正式定義 ETF_TW 狀態分層、instance state 單一真相源、refresh pipeline 與 agent 對齊規則。
- 新增 `docs/SYMBOL_NORMALIZATION.md`，正式定義 canonical symbol 規範與 provider suffix（`.TW` / `.TWO`）邊界。
- 新增 symbol normalization regression tests，覆蓋 canonicalization 與 mapping 行為。

### Changed
- 將 refresh 主鏈與 decision engine 支線進一步收斂為 **instance state only**，避免 dashboard / agent / scripts 讀寫不同狀態檔。
- `refresh_monitoring_state.py` 正式納入 `market_event_context`、`market_context_taiwan`、`major_event_flag`，補齊市場上下文刷新鏈。
- `sync_market_cache.py`、`sync_ohlcv_history.py`、`sync_agent_summary.py` 已改為 canonical symbol 導向，降低 watchlist / tape / summary 的重複訊號。
- README、dashboard runbook、TASKS 已更新正式架構原則，明確要求 agent 與 ETF_TW 長期資訊對齊。

### Fixed
- 修正多支腳本仍硬寫 root `state/`，導致 instance-aware dashboard 與 agent 看到不同狀態來源的問題。
- 修正 watchlist 中 `.TW` provider symbol 進入 state，造成 `0050` / `0050.TW` 等重複訊號的問題。
- 修正 `agent_summary` 關鍵指標摘要會重複顯示 canonical 與 provider variant symbol 的問題。

### Validation
- `verify_alignment.py`：通過
- `verify_decision_engine_stability.py`：通過
- refresh 主鏈重跑：通過
- regression tests：11 passed

## v1.2.1 — 2026-03-30
### Fixed
- 正式釐清 Shioaji live 持股數量語義：**必須使用 `list_positions(..., unit=Unit.Share)`**
- 修正先前誤用 `Unit.Common` 導致 0050 / 00878 股數被讀成 0 的問題
- dashboard / state / agent 現已對齊到 `Unit.Share` 規則

### Locked Rules
- `Unit.Share` 是 live 持股數量真相源
- `Unit.Common` 不得再用於真實持股數顯示
- 若未來再出現 live 持股誤顯示為 0，視為 regression
