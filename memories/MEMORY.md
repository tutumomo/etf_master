§
§
### 教訓34：Hermes ollama-cloud provider 環境變數名稱
- hermes ollama-cloud provider 用 `OLLAMA_API_KEY`（不是 `OLLAMA_CLOUD_API_KEY`）和 `OLLAMA_BASE_URL`（不是 `OLLAMA_CLOUD_BASE_URL`）
- Agent .env 需同時有 `OLLAMA_API_KEY` + `OLLAMA_BASE_URL=https://ollama.com/v1`
- 系統 .env 的 `OLLAMA_CLOUD_API_KEY`/`OLLAMA_CLOUD_BASE_URL` 是舊名，hermes 不讀
- 已在兩個 .env 都補上 `OLLAMA_API_KEY` + `OLLAMA_BASE_URL`
§
§
### 教訓35：Shioaji market_value 永遠回傳 0
- `api.account_balance().balance.market_value` 恆為 0（Shioaji API 已知行為）
- `sync_live_state.py` 已修：API=0 時從 positions 算 market_value（position-level mv → fallback qty×price），total_equity 同步重算
- 修後：market_value 0→54814.95, total_equity 47526→102340.95，與 portfolio_snapshot 吻合
§
### 教訓36：Dashboard 404 + 殘留進程
- 新增路由後 dashboard 未重啟 → 舊進程跑舊 app.py → 404
- 排查：端點在 app.py？→ 是 → 重啟 dashboard → 順手清 5050/5051 殘留
- 官方 port = 5055；5050/5051 是舊實例直接 kill
§
### 教訓37：Wiki 檔案 git 追蹤路徑
- `skills/ETF_TW/instances/*/wiki/` 被 `.gitignore` 排除（instances/ 整個目錄不追蹤）
- 若要 commit wiki 知識頁，必須放在 `skills/ETF_TW/wiki/`（非 instances 下）
- instances wiki 是工作副本，`skills/ETF_TW/wiki/` 是 git 追蹤副本
- 寫入 wiki 時應同時寫兩處，或 commit 前手動 cp
§
### 教訓38：risk_context_summary 假接線修復
- `ai_decision_response.json` 的 reasoning 3 欄位是空字串的根因：舊版 `generate_ai_decision_response.py` 用 `build_ai_decision_response()` 只產空 reasoning
- 新版 `generate_ai_agent_response.py` 有 `_build_agent_reasoning()` 能正確從 decision_reasoning.json + worldmonitor_context + event_context 生成 reasoning
- 修法：在 `refresh_decision_engine_state.py` 的 SCRIPTS 清單加入 `generate_ai_agent_response.py`（在 `run_auto_decision_scan.py` 之後）
- Commit: c48d7ad
- 驗證：管線後 `ai_decision_response.json` source 變為 `ai_agent`，risk_context_summary 包含 worldmonitor 信號
§
### 教訓39：Shioaji 三大日常操作 API 速查（背起來，不准再找）
- **查持倉**：`adapter.get_positions('0737121')` → 回傳 Position 物件列表
- **查委託/成交**：`api.order_deal_records(api.stock_account, timeout=10000)` → 回傳 OrderDealRecords 列表（record.order 有 code/action/price/qty/order_type，record.operation.op_type="New"=已送出，record.contract.code=標的代碼）
- **下單**：`adapter.submit_order(Order(symbol=..., action='buy', quantity=100, price=..., order_type='limit', account_id='0737121', mode='live', status='pending'))`
- ❌ `api.list_trades()` 經常回傳空，不可靠，不要用它查委託
- ❌ `api.list_orders()` 不存在
- ❌ `api.list_today_trades()` 不存在
- ❌ `api.order_deal_records()` 不接受日期參數，簽名是 (account, timeout=5000, cb=None)
- ⚠️ Shioaji process 結束後容易 segfault，查完就收
§
### 教訓40：錯誤訊息零容忍原則
- 早期系統剛建立時，小錯（404、warning、fallback noisy log）可以暫緩修
- 但一旦系統進入日常運作，任何持續產生的錯誤訊息都必須立即排除根因，不得「無視它」
- 每一條噴出的 error/warning 都是技術債，拖越久越難追
- 原則：看到錯 → 當次就修 → commit，不留「下次再說」
§
### 教訓41：台灣ETF交易規則核心（必記）
- ROD = 當日有效，收盤即失效，不跨日！次日須重新下單
- 零股僅接受限價ROD，不可改價（只能減量或取消重掛）
- 盤中零股未成交不保留至盤後零股時段
- ETF不適用盤後定價交易（14:00-14:30那段）
- 週末/非交易時段下的單 = 預約單，次日08:30券商轉送交易所
- Shioaji API 無「長效單」，跨日掛單須 re-submit
- 升降單位：ETF固定0.01；漲跌幅±10%（國外成分ETF無限制）
- 已內化為 skill: etf-tw-trading-rules
§
### 教訓42：Hermes API Server（8642）啟動要點
- API Server 是 gateway 的 platform adapter，預設不啟用
- 啟用：config.yaml 加 `platforms.api_server.enabled: true`
- Key 設定：profile 目錄下 .env 的 `API_SERVER_KEY`（非全域 .env）
- config.yaml 中 key 放 `extra.key` 底下（from_dict 只讀 extra dict）
- 重啟 gateway 生效：`hermes gateway restart --profile etf_master`
- 驗證：`curl -H "Authorization: Bearer <key>" http://localhost:8642/v1/models`
- 端點：health、v1/models、v1/chat/completions、v1/responses
§
### OWUI Code Interpreter能力地圖(詳見skill:open-webui-output-formats)
- Pyodide瀏覽器WASM沙盒，禁pip/shell/C-ext
- 內建numpy/pandas/matplotlib/scikit-learn/scipy/requests/bs4
- 適合：即時分析/圖表/金融計算/檔案處理/原型驗證
- 不適合：大型開發/系統操作/自訂套件/高效能計算
- Code Interpreter語法：<code_interpreter>XML標籤（非三反引號）
- 與Open Terminal互斥
§
### 教訓 43：Karpathy 修正案與極簡主義開發原則 (Simplicity First)
- **原則：** 執行「極簡主義」，拒絕 AI 過度工程化與投機性抽象。若 50 行代碼能解決問題，禁止寫成 200 行架構。
- **規則：** 
  1. **零抽象**：禁止為單一用途邏輯建立介面、工廠或基類。
  2. **先定義成功**：動手前必列「成功指標」與「失敗案例」。
  3. **外科手術修改**：禁止「順便」重構。只觸動目標相關代碼。
  4. **主動推回 (Push Back)**：若使用者要求會導致臃腫，必須質疑其必要性並提議更簡單的方案。
- **目標：** 減少 80% 的廢代碼，確保每一行代碼都有明確的測試與存在意義。
- 詳見根目錄 `GEMINI.md`。
§
### 家族 Agent + 教訓44
- 4 profile：etf_master(5055), etf_wife(太太/5056), etf_son(少爺/5057), etf_daughter(千金/5058)
- 家人全 paper 模式，模型同用 ollama-cloud glm-5.1:cloud
- skills/ + wiki/ symlink → etf_master；SOUL.md/instances/config.yaml/.env 各自獨立
- 教訓44：positions.json 空=必須 {"positions":[]} 不能 []，orders_open 同理，否則 dashboard 500