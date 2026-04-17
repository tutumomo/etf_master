# ROADMAP: ETF_TW 穩定化與保險絲收斂

**Created:** 2026-04-15
**Granularity:** Standard
**Core Value:** 交易安全優先於功能完備 -- 保險絲能擋住錯誤指令，比新增功能更重要

## Phases

- [x] **Phase 00: 盤點與凍結** -- 釐理 active/legacy 路徑，建立只改 active 副本的明文規範 (COMPLETE)
- [x] **Phase 01: 真真真相層級治理** -- 文件與程式回應統一三層分級，消除 state 過度信任殘留，決策控制台建議決策落地 (COMPLETE)
- [x] **Phase 02: 交易保險絲收斂** -- sizing policy + pre-flight gate 單一路徑化，submit 後強制落地驗證，交易閾值設定 (COMPLETE)
- [x] **Phase 03: 持倉交易票據 UI** -- drawer 展開票據、preview/confirm/submit 三段式、維持人工確認、可摺疊區塊、新手泡泡說明 (COMPLETE)
- [x] **Phase 04: 回歸測試與版本保全** -- 五類回歸案例覆蓋、全流程 commit hash、push 到 GitHub (COMPLETE)
- [x] **Phase 05: 財經技能整合與 SOUL 升級** -- 深度檢視 3 個財經技能並建立意圖觸發映射表 (COMPLETE)
- [x] **Phase 06: 決策對齊與反應式引擎** -- 確保建議對齊策略與情境，並實作即時連動 (COMPLETE, 2026-04-17)
- [x] **Phase 07: Dashboard 持倉與關注區塊整合** -- 合併區塊、優化交易票據、動態買賣邏輯 (COMPLETE, 2026-04-16)
- [x] **Phase 08: Dashboard UI 優化與一鍵同步** -- 實作「一鍵全同步」並精簡冗餘按鈕 (COMPLETE, 2026-04-17)
- [x] **Phase 09: 交易閾值與 AI 絕對紅線系統 (Safety Redlines)** -- 實作硬性閾值管理與交易攔截 (COMPLETE, 2026-04-17)
- [x] **Phase 10: 決策品質驗證與 Live Submit 解鎖** -- Paper mode 壓力測試、決策審計報告、sinopac adapter 接通、授權閘門 UI (COMPLETE, 2026-04-17)

## Phase Details

### Phase 00: 盤點與凍結

**Goal**: 先把 active/legacy 路徑、修改政策與混線風險盤點清楚，避免後續修正打到錯副本。
**Depends on**: None
**Requirements**: PATH-01, PATH-02, PATH-03
**Success Criteria** (what must be TRUE):
  1. active/legacy 路徑報表存在且可檢查。
  2. 只改 active 副本的明文政策已落盤。
  3. 主要腳本不再混用 legacy 路徑。
**Plans**: 3 plans
- [x] 00-01-PLAN.md — 建立系統路徑盤點報表 (PATH-01)
- [ ] 00-02-PLAN.md — Active/Legacy 對照與修改政策明文化 (PATH-02)
- [x] 00-03-PLAN.md — Legacy 路徑 grep audit 與混線修正 (PATH-03)

### Phase 01: 真真真相層級治理

**Goal**: 將文件、查詢與 Dashboard 顯示統一到「交易所 / 券商 / 本地 state」三層真相模型，避免把本地檔案誤稱唯一真相。
**Depends on**: Phase 00
**Requirements**: TRUTH-01, TRUTH-02, TRUTH-03, TRUTH-04, TRUTH-05
**Success Criteria** (what must be TRUE):
  1. 文件與 UI 不再把本地 state 表述成唯一真相源。
  2. 查詢結果帶有 truth layer 標註。
  3. AI Decision Bridge / Consensus 鏈路與 Dashboard 雙軌建議一致反映真相層級。
**Plans**: 3 plans
- [ ] 01-01-PLAN.md — 文件與術語去除「唯一真相源」表述 (TRUTH-01, TRUTH-02)
- [ ] 01-02-PLAN.md — 查詢邏輯整合 truth layer 標註 (TRUTH-03)
- [ ] 01-03-PLAN.md — AI / Dashboard 雙軌建議真相層級落地 (TRUTH-04, TRUTH-05)

### Phase 02: 交易保險絲收斂

**Goal**: 把 sizing、pre-flight gate、submit 後落地驗證與交易閾值收斂成單一路徑。
**Depends on**: Phase 01
**Requirements**: FUSE-01, FUSE-02, FUSE-03, FUSE-04, FUSE-05, FUSE-06
**Success Criteria** (what must be TRUE):
  1. sizing policy 與 pre-flight gate 為唯一進場檢查路徑。
  2. submit 後必須經過落地驗證。
  3. 閾值設定能回饋到監控與下單建議。
**Plans**: 3 plans
- [x] 02-01-PLAN.md — sizing engine v1 + unified pre_flight_gate (FUSE-01, FUSE-02, FUSE-03)
- [ ] 02-02-PLAN.md — submit 驗證與 adapter 整合 (FUSE-04, FUSE-05)
- [ ] 02-03-PLAN.md — 閾值設定、監控建議與 UI 鉤子 (FUSE-06)

### Phase 03: 持倉交易票據 UI

**Goal**: 建立安全的票據展開、preview/confirm/submit 三段式下單體驗與新手導引。
**Depends on**: Phase 02
**Requirements**: TICKET-01, TICKET-02, TICKET-03, TICKET-04, TICKET-05, TICKET-06, TICKET-07
**Success Criteria** (what must be TRUE):
  1. 卡片可摺疊、具 Tooltip 與 onboarding hints。
  2. 持倉主列可展開票據並編輯下單參數。
  3. preview / confirm / submit 狀態流轉完整。
**Plans**: 3 plans
- [x] 03-01-PLAN.md — 可摺疊卡片、Tooltip 與新手引導 (TICKET-01, TICKET-02)
- [x] 03-02-PLAN.md — 持倉主列交易入口與票據展開層 (TICKET-03, TICKET-04)
- [x] 03-03-PLAN.md — preview / submit API 與票據狀態流轉 (TICKET-05, TICKET-06, TICKET-07)

### Phase 04: 回歸測試與版本保全

**Goal**: 用回歸測試與版本保全把核心交易流程鎖住，避免後續重構造成行為回退。
**Depends on**: Phase 03
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, GIT-01, GIT-02, GIT-03
**Success Criteria** (what must be TRUE):
  1. odd-lot、空回應、未落地語義與票據狀態流轉皆有測試覆蓋。
  2. sizing 政策變更有回歸保護。
  3. 版本保全含 commit hash 蒐集與遠端推播。
**Plans**: 3 plans
- [x] 04-01-PLAN.md — Odd-lot / 空回應 / 未落地語義回歸測試 (TEST-01, TEST-02, TEST-03)
- [x] 04-02-PLAN.md — 票據狀態流轉與 sizing 生效回歸測試 (TEST-04, TEST-05)
- [x] 04-03-PLAN.md — 版本保全與 GitHub 推播 (GIT-01, GIT-02, GIT-03)

### Phase 05: 財經技能整合與 SOUL 升級

**Goal**: 修好外部財經技能的可執行性，並把分析結果與 SOUL 意圖映射接回 ETF_master。
**Depends on**: Phase 04
**Requirements**: SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05
**Success Criteria** (what must be TRUE):
  1. `stock-analysis-tw`、`stock-market-pro-tw`、`taiwan-finance` 在當前環境可正常使用。
  2. 技能結果能寫回 etf_master state。
  3. SOUL.md 有清楚的意圖觸發映射，並完成模擬意圖驗證。
**Plans**: 3 plans
- [x] 05-01-PLAN.md — 財經技能腳本審計與執行修復 (SKILL-01, SKILL-02)
- [x] 05-02-PLAN.md — 技能結果整合與 SOUL 意圖映射 (SKILL-03, SKILL-04)
- [x] 05-03-PLAN.md — 模擬意圖驗證與收尾 (SKILL-05)

### Phase 06: 決策對齊與反應式引擎

**Goal**: 確保規則引擎與 AI Bridge 的建議 100% 對齊用戶設定的「投資策略」與「情境覆蓋」，並實作 Dashboard 的反應式即時連動。
**Depends on**: Phase 05
**Requirements**: ALIGN-01, ALIGN-02, ALIGN-03, ALIGN-04, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 規則引擎能根據 `base_strategy` (收益/累積) 自動調整評分權重。
  2. AI Bridge 的 Prompt 強制引用策略依據，且 reasoning 包含策略檢核。
  3. Dashboard 切換策略後，雙鏈建議 (Rule/AI) 自動重新掃描並清除舊狀態。
  4. 仲裁邏輯在衝突時，優先選擇符合當前策略方向的決策。
**Plans**: 3 plans
- [x] 06-01-PLAN.md — Rule Engine 動態權重矩陣實作 (ALIGN-01)
- [x] 06-02-PLAN.md — AI Bridge 指令強化與仲裁優化 (ALIGN-02, ALIGN-04)
- [x] 06-03-PLAN.md — Dashboard 反應式連動與整合驗證 (ALIGN-03)

### Phase 07: Dashboard 持倉與關注區塊整合

**Goal**: 透過合併區塊與優化交易票據，提升 Dashboard 資訊密度與操作安全性，實作動態交易權限與預覽模式。
**Depends on**: Phase 06
**Requirements**: UI-INTEGRATE, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 「關注標的」與「盤感輔助層」成功合併，顯示完整指標。
  2. 持倉區塊與關注區塊的交易票據預設值為 100 股。
  3. 未持倉標的僅能執行「買入」，已持倉標的支援雙向交易。
  4. 交易票據顯式標記「Preview Only」。
**Plans**: 2 plans
- [x] 07-01-PLAN.md — 盤感與關注區塊合併 UI (UI-INTEGRATE)
- [x] 07-02-PLAN.md — 持倉優化與動態下單邏輯 (UI-INTEGRATE)

### Phase 08: Dashboard UI 優化與一鍵同步

**Goal**: 優化 Dashboard UI 指令集，實作「一鍵全同步」整合端點，並移除冗餘按鈕，優化 UI 佈局。
**Depends on**: Phase 07
**Requirements**: UI-STREAMLINE, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 建立 /api/decision/full-pipeline 整合管線執行腳本。
  2. Dashboard 頂部新增醒目的「一鍵同步與全量分析」按鈕。
  3. 移除 Dashboard 中至少 5 個獨立的手動刷新按鈕。
  4. 策略更新後自動啟動全量同步流程。
**Plans**: 3 plans
- [x] 08-01-PLAN.md — [Backend] /api/decision/full-pipeline 整合實作 (UI-STREAMLINE)
- [x] 08-02-PLAN.md — [Frontend] UI 整合與按鈕精簡 (UI-STREAMLINE)
- [x] 08-03-PLAN.md — [Integration] 策略變動連動與驗證 (UI-STREAMLINE)

### Phase 09: 交易閾值與 AI 絕對紅線系統 (Safety Redlines)

**Goal**: 在 Dashboard 建立交易閾值管理 UI，並將參數硬性整合進 `pre_flight_gate.py` 作為絕對紅線阻斷機制。
**Depends on**: Phase 2, Phase 7, Phase 8
**Requirements**: FUSE-V3-REDLINE
**Success Criteria** (what must be TRUE):
  1. Dashboard 新增「交易閾值 / Safety Redlines」區塊且支援保存設定。
  2. 所有閾值參數 (金額、股數、集中度、日虧損、AI 信心) 成功持久化。
  3. `pre_flight_gate.py` 能正確攔截超限訂單 (金額/股數/集中度)。
  4. 日虧損熔斷機制在 `daily_pnl` 超標時阻斷所有買入指令。
  5. 低於 AI 信心門檻的 AI 建議下單被攔截。
  6. 回歸測試模擬各類超限情境並確認攔截成功。
**Plans**: 3 plans
- [x] 09-01-PLAN.md — [Backend] 閾值儲存與 pre_flight_gate 絕對紅線整合 (FUSE-V3-REDLINE)
- [x] 09-02-PLAN.md — [Frontend] Dashboard 閾值管理區塊與 Tooltips (FUSE-V3-REDLINE)
- [x] 09-03-PLAN.md — [Testing] 超限阻斷回歸測試撰寫 (FUSE-V3-REDLINE)

### Phase 10: 決策品質驗證與 Live Submit 解鎖

**Goal**: 在解鎖真實下單前建立可驗證的決策品質證據，並安全接通 sinopac live submit 路徑。
**Depends on**: Phase 06, Phase 9
**Requirements**: QUALITY-01, QUALITY-02, QUALITY-03, LIVE-01, LIVE-02, LIVE-03
**Success Criteria** (what must be TRUE):
  1. `decision_quality_report.json` 自動產生，包含策略對齊率、信心分佈、攔截率統計。
  2. Paper mode 跑 N 輪自動決策掃描，Tier 1/2/3 仲裁分佈正常，無幽靈委託。
  3. `sinopac_adapter` 完整接通 live submit，通過 `list_trades()` 落地驗證。
  4. Dashboard「解鎖 Live 模式」授權閘門實作，需雙重確認 + Safety Redlines 明文展示。
  5. Live submit 回歸測試覆蓋：preview → confirm → submit → verify 完整週期含失敗場景。
  6. 回測框架對 `ai_decision_outcome.jsonl` 計算勝率/最大回撤，決策品質達門檻後方可解鎖。
**Plans**: 6 plans
- [x] 10-01-PLAN.md — [決策審計] 決策品質報告框架與統計指標 (QUALITY-01)
- [x] 10-02-PLAN.md — [壓力測試] Paper mode N 輪掃描與幽靈委託檢測 (QUALITY-02)
- [x] 10-03-PLAN.md — [回測] ai_decision_outcome 勝率/回撤回測框架 (QUALITY-03)
- [x] 10-04-PLAN.md — [Live Submit] sinopac_adapter 接通與 list_trades() 落地驗證 (LIVE-01)
- [x] 10-05-PLAN.md — [授權閘門] Dashboard Live 模式解鎖 UI 與雙重確認 (LIVE-02)
- [x] 10-06-PLAN.md — [回歸測試] Live submit 完整週期含失敗場景測試 (LIVE-03)

**Mandatory Reporting Format:**
1. 本階段做了什麼（3~6行）
2. 修改檔案清單（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash（未commit不得回報完成）

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 00 | Completed |
| PATH-02 | Phase 00 | Completed |
| PATH-03 | Phase 00 | Completed |
| TRUTH-01 | Phase 01 | Completed |
| TRUTH-02 | Phase 01 | Completed |
| TRUTH-03 | Phase 01 | Completed |
| TRUTH-04 | Phase 01 | Completed |
| TRUTH-05 | Phase 01 | Completed |
| FUSE-01 | Phase 02 | Completed |
| FUSE-02 | Phase 02 | Completed |
| FUSE-03 | Phase 02 | Completed |
| FUSE-04 | Phase 02 | Completed |
| FUSE-05 | Phase 02 | Completed |
| FUSE-06 | Phase 02 | Completed |
| TICKET-01 | Phase 03 | Completed |
| TICKET-02 | Phase 03 | Completed |
| TICKET-03 | Phase 03 | Completed |
| TICKET-04 | Phase 03 | Completed |
| TICKET-05 | Phase 03 | Completed |
| TICKET-06 | Phase 03 | Completed |
| TICKET-07 | Phase 03 | Completed |
| TEST-01 | Phase 04 | Completed |
| TEST-02 | Phase 04 | Completed |
| TEST-03 | Phase 04 | Completed |
| TEST-04 | Phase 04 | Completed |
| TEST-05 | Phase 04 | Completed |
| SKILL-01 | Phase 05 | Completed |
| SKILL-02 | Phase 05 | Completed |
| SKILL-03 | Phase 05 | Completed |
| SKILL-04 | Phase 05 | Completed |
| SKILL-05 | Phase 05 | Completed |
| ALIGN-01 | Phase 06 | Completed |
| ALIGN-02 | Phase 06 | Completed |
| ALIGN-03 | Phase 06 | Completed |
| ALIGN-04 | Phase 06 | Completed |
| UI-INTEGRATE | Phase 07 | Completed |
| UI-STREAMLINE | Phase 08 | Completed |
| FUSE-V3-REDLINE | Phase 09 | Completed |
| GIT-01 | All Phases | Completed |
| GIT-02 | All Phases | Completed |
| GIT-03 | Phase 04 | Completed |

| QUALITY-01 | Phase 10 | Completed |
| QUALITY-02 | Phase 10 | Completed |
| QUALITY-03 | Phase 10 | Completed |
| LIVE-01 | Phase 10 | Completed |
| LIVE-02 | Phase 10 | Completed |
| LIVE-03 | Phase 10 | Completed |

**Mapped: 47/47 requirements**

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
| 5. 財經技能整合與 SOUL 升級 | 3/3 | Completed | 2026-04-16 |
| 6. 決策對齊與反應式引擎 | 3/3 | Completed | 2026-04-17 |
| 7. Dashboard 持倉與關注區塊整合 | 2/2 | Completed | 2026-04-16 |
| 8. Dashboard UI 優化與一鍵同步 | 3/3 | Completed | 2026-04-17 |
| 9. 交易閾值與 AI 絕對紅線系統 | 3/3 | Completed | 2026-04-17 |
| 10. 決策品質驗證與 Live Submit 解鎖 | 6/6 | Completed | 2026-04-17 |
