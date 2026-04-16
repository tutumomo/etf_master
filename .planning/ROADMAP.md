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
- [x] **Phase 5: 財經技能整合與 SOUL 升級** -- 深度檢視 3 個財經技能並建立意圖觸發映射表 (COMPLETE)
- [ ] **Phase 6: 決策對齊與反應式引擎** -- 確保建議對齊策略與情境，並實作即時連動 (IN PROGRESS)

## Phase Details

### Phase 5: 財經技能整合與 SOUL 升級

**Goal**: 確保三個財經技能 (stock-analysis-tw, stock-market-pro-tw, taiwan-finance) 腳本正確且已整合至 SOUL.md 的意圖映射表。
**Depends on**: Phase 4
**Requirements**: SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 三個技能的腳本可在當前環境執行，不報路徑引用或依賴錯誤。
  2. 技能分析結果能正確參考或寫入 `instances/etf_master/state/` 目錄。
  3. `SOUL.md` 新增「意圖觸發映射表」，定義買賣建議、診斷詢問、線圖請求、估值請求的對應技能。
  4. 模擬提問驗證 Agent 能正確選擇技能執行。
**Plans**: 3 plans
- [x] 05-01-PLAN.md — 財經技能審計與路徑依賴修復 (SKILL-01, SKILL-02)
- [x] 05-02-PLAN.md — 狀態整合與 SOUL 意圖映射表建立 (SKILL-03, SKILL-04)
- [x] 05-03-PLAN.md — 整合驗證與情境模擬 (SKILL-05)

### Phase 6: 決策對齊與反應式引擎

**Goal**: 確保規則引擎與 AI Bridge 的建議 100% 對齊用戶設定的「投資策略」與「情境覆蓋」，並實作 Dashboard 的反應式即時連動。
**Depends on**: Phase 5
**Requirements**: ALIGN-01, ALIGN-02, ALIGN-03, ALIGN-04, GIT-01, GIT-02
**Success Criteria** (what must be TRUE):
  1. 規則引擎能根據 `base_strategy` (收益/累積) 自動調整評分權重。
  2. AI Bridge 的 Prompt 強制引用策略依據，且 reasoning 包含策略檢核。
  3. Dashboard 切換策略後，雙鏈建議 (Rule/AI) 自動重新掃描並清除舊狀態。
  4. 仲裁邏輯在衝突時，優先選擇符合當前策略方向的決策。
**Plans**: 3 plans
- [ ] 06-01-PLAN.md — Rule Engine 動態權重矩陣實作 (ALIGN-01)
- [ ] 06-02-PLAN.md — AI Bridge 指令強化與仲裁優化 (ALIGN-02, ALIGN-04)
- [ ] 06-03-PLAN.md — Dashboard 反應式連動與整合驗證 (ALIGN-03)

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
| TICKET-01 | Phase 3 | Completed |
| TICKET-02 | Phase 3 | Completed |
| TICKET-03 | Phase 3 | Completed |
| TICKET-04 | Phase 3 | Completed |
| TICKET-05 | Phase 3 | Completed |
| TICKET-06 | Phase 3 | Completed |
| TICKET-07 | Phase 3 | Completed |
| TEST-01 | Phase 4 | Completed |
| TEST-02 | Phase 4 | Completed |
| TEST-03 | Phase 4 | Completed |
| TEST-04 | Phase 4 | Completed |
| TEST-05 | Phase 4 | Completed |
| SKILL-01 | Phase 5 | Completed |
| SKILL-02 | Phase 5 | Completed |
| SKILL-03 | Phase 5 | Completed |
| SKILL-04 | Phase 5 | Completed |
| SKILL-05 | Phase 5 | Completed |
| ALIGN-01 | Phase 6 | In Progress |
| ALIGN-02 | Phase 6 | In Progress |
| ALIGN-03 | Phase 6 | In Progress |
| ALIGN-04 | Phase 6 | In Progress |
| GIT-01 | All Phases | Completed |
| GIT-02 | All Phases | Completed |
| GIT-03 | Phase 4 | Completed |

**Mapped: 39/39 requirements**

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
| 6. 決策對齊與反應式引擎 | 0/3 | In Progress | - |
