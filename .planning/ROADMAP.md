# ROADMAP: ETF_TW 穩定化與保險絲收斂

**Created:** 2026-04-15
**Granularity:** Standard
**Core Value:** 交易安全優先於功能完備 -- 保險絲能擋住錯誤指令，比新增功能更重要

## Phases

- [x] **Phase 0: 盤點與凍結** -- 釐理 active/legacy 路徑，建立只改 active 副本的明文規範 (COMPLETE)
- [x] **Phase 1: 真相層級治理** -- 文件與程式回應統一三層分級，消除 state 過度信任殘留，決策控制台建議決策落地 (COMPLETE)
- [x] **Phase 2: 交易保險絲收斂** -- sizing policy + pre-flight gate 單一路徑化，submit 後強制落地驗證，交易閾值設定 (COMPLETE)
- [x] **Phase 3: 持倉交易票據 UI** -- drawer 展開票據、preview/confirm/submit 三段式、維持人工確認、可摺疊區塊、新手泡泡說明 (COMPLETE)
- [x] **Phase 4: 回歸測試與版本保全** -- 五類回歸案例覆蓋、全流程 commit hash、push 到 GitHub (COMPLETE)

## Phase Details

### Phase 0: 盤點與凍結

**Goal**: 系統輸出完整路徑清單，明文標示只改 active 副本，確認無路徑混用
**Depends on**: Nothing (first phase)
**Requirements**: PATH-01, PATH-02, PATH-03, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 執行路徑報告指令可輸出 HERMES_HOME、config path、active profile、ETF_TW 工作目錄的完整清單
  2. active/legacy 檔案對照清單已建立，且明文聲明只修改 active 路徑下的檔案
  3. 程式碼 grep 確認無任何地方同時引用 ~/.openclaw 與 ~/.hermes/profiles/etf_master 路徑
**Plans**: 3 plans
- [x] 00-01-PLAN.md — 建立路徑報告工具並紀錄目前生效路徑 (PATH-01)
- [x] 00-02-PLAN.md — 建立檔案對照清單與凍結政策聲明 (PATH-02)
- [x] 00-03-PLAN.md — 修正程式碼路徑混用問題並建立稽核工具 (PATH-03)

**Mandatory Reporting Format:**
1. 本階段做了什麼（3~6行）
2. 修改檔案清單（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash（未commit不得回報完成）

### Phase 1: 真相層級治理

**Goal**: 文件與程式回應統一採用三層分級，消除所有「state=唯一真相源」殘留說法，決策控制台二條建議決策機制落地可用
**Depends on**: Phase 0
**Requirements**: TRUTH-01, TRUTH-02, TRUTH-03, TRUTH-04, TRUTH-05, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 所有對查單回應（文件與程式）均標示資訊來源級別：live API 直接證據 > live 無法確認 > 次級資訊
  2. 活文件中不再有任何「state 是唯一真相源」的說法（歷史 cron 輸出不在此限）
  3. list_trades 空值時的回應採保守措辭：「本次查詢沒看到」，不反推失敗或已成交
  4. submit 回應文字明確標示「仍需後續驗證」，不得暗示委託已落地
  5. 決策控制台二條建議決策全鏈通暢（AI decision bridge request→response→consensus），dashboard 正確顯示
**Plans**: 3 plans
- [x] 01-01-PLAN.md — 真相層級定義與保守措辭 (TRUTH-02, TRUTH-03, TRUTH-04)
- [x] 01-02-PLAN.md — 三層分級標註實作 (TRUTH-01)
- [x] 01-03-PLAN.md — 決策控制台落地與驗證 (TRUTH-05)

**Mandatory Reporting Format:**
1. 本階段做了什麼（3~6行）
2. 修改檔案清單（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash（未commit不得回報完成）

### Phase 2: 交易保險絲收斂

**Goal**: sizing policy 與 pre-flight gate 成為單一不可繞過路徑，submit 後必須進入落地驗證流程，交易閾值可設定
**Depends on**: Phase 1
**Requirements**: FUSE-01, FUSE-02, FUSE-03, FUSE-04, FUSE-05, FUSE-06, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 買賣雙向的 sizing policy 與 pre-flight gate 走同一程式碼路徑，不因買/賣而有不同檢查邏輯
  2. 所有交易前阻擋條件（quantity>0、限價>0、集中度、單筆上限、交易時段、張/股單位、賣出庫存）一致執行
  3. submit 執行後程式自動進入落地驗證流程（list_trades + positions 或其他佐證）
  4. 單元測試證明：超限被擋、超庫存被擋、submit 成功但未落地不被誤報為成功
  5. sizing_engine_v1 可接受輸入（現金、集中度上限、單筆上限、風險溫度）並輸出建議股數、限制原因、是否可下單
  6. 使用者可設定交易閾值（現金百分比等），閾值觸發時可在持倉快照區塊下單（仍受 pre-flight gate 把關）
**Plans**: 3 plans
- [x] 02-01-PLAN.md — 交易保險絲路徑收斂與驗證 (FUSE-01, FUSE-02, FUSE-03, FUSE-04)
- [x] 02-02-PLAN.md — Sizing Engine 整合與建議輸出 (FUSE-05)
- [x] 02-03-PLAN.md — 交易閾值設定與持倉下單入口 (FUSE-06)

**Mandatory Reporting Format:**
1. 本階段做了什麼（3~6行）
2. 修改檔案清單（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash（未commit不得回報完成）

### Phase 3: 持倉交易票據 UI

**Goal**: 持倉主列保持乾淨，交易票據在展開層操作，preview/confirm/submit 三段式且不容許預覽即送單，可摺疊區塊與新手泡泡說明
**Depends on**: Phase 2
**Requirements**: TICKET-01, TICKET-02, TICKET-03, TICKET-04, TICKET-05, TICKET-06, TICKET-07, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 持倉主列只顯示持倉資訊與「交易」入口按鈕，無表單欄位
  2. 交易票據只在 drawer 或 inline detail 展開時出現，不在主列表中塞入表單
  3. 流程為 preview 通過後才顯示確認字串與送出按鈕，不允許跳過 confirm 直接 submit
  4. 送單仍然受 pre-flight gate 與 sizing 限制，不受 auto-preview 開關影響
  5. Dashboard 區塊支援可摺疊收起，使用者可依需求展開/收合
  6. 初次使用者可透過泡泡文字提示理解各區塊意義（tooltip/onboarding hints）
**Plans**: 3 plans
- [x] 03-01-PLAN.md — 儀表板區塊收合與 Tooltip 基礎 (TICKET-06, TICKET-07)
- [x] 03-02-PLAN.md — 持倉交易入口與票據展開層 (TICKET-01, TICKET-02)
- [x] 03-03-PLAN.md — Preview/Confirm/Submit 三段式流程實作 (TICKET-03, TICKET-04, TICKET-05)

**Mandatory Reporting Format:**
1. 本階段做了什麼（3~6行）
2. 修改檔案清單（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash（未commit不得回報完成）

### Phase 4: 回歸測試與版本保全

**Goal**: 五類回歸案例通過，所有 commit hash 齊全，最終 push 到 GitHub
**Depends on**: Phase 3
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, GIT-01, GIT-02, GIT-03
**Success Criteria** (what must be TRUE):
  1. 單位與 odd-lot 回歸案例通過（Common 張 / IntradayOdd 股）
  2. list_trades 空回應語義回歸案例通過（空值不反推失敗或成交）
  3. submit 不等於落地回歸案例通過（submit 成功但未落地時不被誤報）
  4. 持倉票據 preview/confirm/submit 流程回歸案例通過（不允許跳過 confirm）
  5. sizing 政策變更可生效回歸案例通過（政策修改後新計算結果反映變更）
  6. 所有 commit hash 已記錄，push 到 https://github.com/tutumomo/etf_master 並有證據
**Plans**: 3 plans
- [ ] 04-01-PLAN.md — 核心交易邏輯回歸測試 (TEST-01, TEST-02, TEST-03)
- [ ] 04-02-PLAN.md — UI 流程與策略變更回歸測試 (TEST-04, TEST-05)
- [ ] 04-03-PLAN.md — 版本保全與發布 (GIT-01, GIT-02, GIT-03)

**Mandatory Reporting Format:**
1. 本階段做了什麼（3~6行）
2. 修改檔案清單（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash（未commit不得回報完成）

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 0 | Completed |
| PATH-02 | Phase 0 | Completed |
| PATH-03 | Phase 0 | Completed |
| TRUTH-01 | Phase 1 | Completed |
| TRUTH-02 | Phase 1 | Completed |
| TRUTH-03 | Phase 1 | Completed |
| TRUTH-04 | Phase 1 | Completed |
| TRUTH-05 | Phase 1 | Completed |
| FUSE-01 | Phase 2 | Completed |
| FUSE-02 | Phase 2 | Completed |
| FUSE-03 | Phase 2 | Completed |
| FUSE-04 | Phase 2 | Completed |
| FUSE-05 | Phase 2 | Completed |
| FUSE-06 | Phase 2 | Completed |
| TICKET-01 | Phase 3 | Pending |
| TICKET-02 | Phase 3 | Pending |
| TICKET-03 | Phase 3 | Pending |
| TICKET-04 | Phase 3 | Pending |
| TICKET-05 | Phase 3 | Pending |
| TICKET-06 | Phase 3 | Completed |
| TICKET-07 | Phase 3 | Completed |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| TEST-05 | Phase 4 | Pending |
| GIT-01 | All Phases | Pending |
| GIT-02 | All Phases | Pending |
| GIT-03 | Phase 4 | Pending |

**Mapped: 30/30 requirements**

## Hard Constraints

1. 禁止混用 OpenClaw 舊路徑與 Hermes active 路徑
2. 禁止把 state/dashboard 當成 live 事實
3. 禁止「submit 回傳成功」就宣告委託已落地
4. 所有正式送單路徑必須走 pre-flight gate
5. 每個階段必須 commit，最終必須 push
6. 只改 active 副本，不改歷史輸出當現行規則

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. 盤點與凍結 | 3/3 | Completed | 2026-04-15 |
| 1. 真相層級治理 | 3/3 | Completed | 2026-04-15 |
| 2. 交易保險絲收斂 | 3/3 | Completed | 2026-04-15 |
| 3. 持倉交易票據 UI | 3/3 | Completed | 2026-04-16 |
| 4. 回歸測試與版本保全 | 3/3 | Completed | 2026-04-16 |