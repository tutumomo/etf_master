# ETF_TW / Hermes 遷移後穩定化與交易流程保險絲收斂計劃

## What This Is

ETF_TW 是一個建構在 Hermes Agent 上的台灣 ETF 投資助理，核心功能包含持倉管理、自動決策掃描、Shioaji 券商下單、dashboard 監控。經歷 kimi-2.7 錯誤下單事件後，需要把已有的修復成果正式化，並補齊交易保險絲、真相層級治理、持倉交易票據等功能，產出可驗證、可回滾、可追蹤的變更紀錄。

## Core Value

**交易安全優先於功能完備** — 任何時候，保險絲能擋住錯誤指令，比新增功能更重要。

## Requirements

### Validated

<!-- 已從歷史修復驗證的能力 -->

- ✓ P0-1：文件中「state=唯一真相」殘留說法已清除（SKILL.md、AI_DECISION_BRIDGE.md、BROKER_RECONCILIATION_RULES.md、STATE_ARCHITECTURE.md、README.md）
- ✓ P0-2：list_trades() 空值不再被誤解讀成「沒下單/已成交」
- ✓ P0-3：submit 回應不再被等同於「委託已落地」（complete_trade.py、dashboard/app.py 已修）
- ✓ P0-4：股/張/order_lot 單位邏輯已在 adapter 層收正（sinopac_adapter.py、sinopac_adapter_enhanced.py）
- ✓ sizing_interface.py 已建立（placeholder_preview → sizing_engine_v1）
- ✓ pre-flight gate 已接到送單前（sizing / 集中度 / 單筆 / 庫存檢查）
- ✓ 持倉交易票據 UI 已做成展開 drawer 式（不在主表塞表單）
- ✓ dashboard source label / 交通燈色塊已上線

### Active

<!-- 本次計劃要完成的需求 -->

- [ ] 路徑盤點與凍結：釐清 active vs legacy 路徑，明文寫出只改 active
- [ ] 真相層級治理：文件+程式一致採用三層誠實分層（live > state > fallback）
- [ ] 交易保險絲收斂：sizing policy + pre-flight gate 單一路徑化、submit 後必須進落地驗證
- [ ] 持倉交易票據 UI：preview/confirm/submit 三段式、不受 auto-preview 限制、仍受 pre-flight 控制
- [ ] 回歸測試覆蓋：單位/odd-lot、list_trades 空值語義、submit≠落地、持倉票據流程、sizing 生效
- [ ] Git 憑證齊全：每階段 commit+hash，最終 push+證據

### Out of Scope

- 路徑自動遷移工具 — 只盤點不改歷史路徑結構
- AI 自主下單（Stage 3+）— 本次只做保險絲，不開放 agent 自動送單
- 其他 skill（stock-analysis-tw、taiwan-finance）的功能增強
- Dashboard 美化/響應式設計 — 只做功能對齊，不做視覺重構

## Context

**已發生的 kimi-2.7 錯誤下單事件：**
AI 模型在缺乏保險絲的情況下直接觸碰交易，造成真實風險。這是本次所有工作的根本驅動力。

**4/14 修復歷史（已做但缺正式管控）：**
Hermes agent session 內完成了 P0-1 到 P0-4 的文件與程式修復、P2 的 sizing engine / pre-flight gate / 交易票據 UI。但因為是 session 內操作，缺乏：
- 逐階段 commit hash
- 回歸測試
- 可回滾的版本憑證
- formal 的驗證報告

**已知高風險歷史問題（需防回歸）：**
1. 路徑混用（~/.openclaw 與 ~/.hermes/profiles/etf_master）
2. 「查不到 list_trades」被誤推論成沒下單/已成交
3. 股/張與 order_lot 邏輯混淆
4. 文案把 state 說成唯一真相源
5. UI 把交易票據塞進持倉主列造成可讀性崩壞（已修但仍需回歸測試）
6. 回報過度自信（說已推送但缺可驗證證據）

## Constraints

- **Tech:** Python 3.14+ / Shioaji SDK / FastAPI dashboard / Hermes Agent framework
- **Timeline:** 優先完成保險絲收斂，再處理 UI
- **Trading hours:** 09:00-13:30（一般）、13:40-14:30（盤後零股）
- **硬限制：**
  1. 禁止混用 OpenClaw 舊路徑與 Hermes active 路徑
  2. 禁止把 state/dashboard 當成 live 事實
  3. 禁止「submit 回傳成功」就宣告委託已落地
  4. 禁止用過時單位口號（非 1000 倍數一定拒絕）
  5. 所有正式送單路徑必須走 pre-flight gate
  6. 每個階段必須 commit，最終必須 push
  7. 只改 active 副本，不改歷史輸出當現行規則

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 真相三層級：live > state > fallback | 避免 state 被過度信任 | — Pending |
| sizing_engine_v1 作為正式 sizing 介面 | 取代 quantity=100 的 placeholder | — Pending |
| 持倉票據走 drawer 不走主列 | 保持持倉表可讀性 | — Pending |
| preview → confirm → submit 三段式 | 不允許預覽即送單 | — Pending |

---

*Last updated: 2026-04-15 after initialization*