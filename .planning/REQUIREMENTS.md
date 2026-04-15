# Requirements: ETF_TW 穩定化與保險絲收斂

**Defined:** 2026-04-15
**Core Value:** 交易安全優先於功能完備 — 保險絲能擋住錯誤指令，比新增功能更重要

## v1 Requirements

### 路徑治理 (PATH)

- [ ] **PATH-01**: 系統輸出目前生效路徑清單（HERMES_HOME、config path、active profile、ETF_TW 工作目錄）
- [ ] **PATH-02**: 建立 active/legacy 檔案對照清單，明文標示只改 active 路徑
- [ ] **PATH-03**: 確認無混用 ~/.openclaw 與 ~/.hermes/profiles/etf_master 路徑的程式碼

### 真相層級 (TRUTH)

- [ ] **TRUTH-01**: 文件與程式回應統一採用三層分級：live API 直接證據 > live 無法確認 > 次級資訊（state/dashboard）
- [ ] **TRUTH-02**: 清除所有「state=唯一真相源」殘留說法（活文件，不含歷史 cron 輸出）
- [ ] **TRUTH-03**: 對查單回應強制採保守措辭（list_trades 空值=本次查詢沒看到，不反推失敗或已成交）
- [ ] **TRUTH-04**: submit 回應不等同委託落地，所有 submit 結果須標示「仍需後續驗證」

### 交易保險絲 (FUSE)

- [ ] **FUSE-01**: sizing policy 與 pre-flight gate 單一路徑化（買賣皆適用，不因路徑不同而雙標）
- [ ] **FUSE-02**: 交易前阻擋條件一致化（quantity>0、限價>0、集中度、單筆上限、交易時段、張/股單位、賣出庫存檢查）
- [ ] **FUSE-03**: submit 後必須進入落地驗證流程（list_trades + positions/其他佐證）
- [ ] **FUSE-04**: 風控限制可準確擋單（單元測試證明：超限被擋、超庫存被擋、submit成功但未落地不被誤報成功）
- [ ] **FUSE-05**: sizing_engine_v1 正式計算規則（輸入：現金、集中度上限、單筆上限、風險溫度；輸出：建議股數、限制原因、是否可下單）

### 持倉交易票據 (TICKET)

- [ ] **TICKET-01**: 持倉主列保持乾淨，只留「交易」入口按鈕
- [ ] **TICKET-02**: 交易票據放在展開層（drawer/inline detail），不在主列塞表單
- [ ] **TICKET-03**: preview → confirm → submit 三段式（預覽通過後才顯示確認字串 + 送出按鈕）
- [ ] **TICKET-04**: 維持人工確認，不允許預覽即送單
- [ ] **TICKET-05**: 送單仍受 pre-flight 與權限控制（不受 auto-preview 限制，但受 sizing + 風控限制）

### 回歸測試 (TEST)

- [ ] **TEST-01**: 單位與 odd-lot 回歸案例（Common 張/IntradayOdd 股）
- [ ] **TEST-02**: list_trades 空回應語義回歸案例
- [ ] **TEST-03**: submit≠落地回歸案例
- [ ] **TEST-04**: 持倉票據 preview/confirm/submit 流程回歸案例
- [ ] **TEST-05**: sizing 政策變更可生效回歸案例

### 版本憑證 (GIT)

- [ ] **GIT-01**: 每階段必須 commit，最終必須 push 到 https://github.com/tutumomo/etf_master
- [ ] **GIT-02**: commit 訊息包含範圍與目的（fix/refactor/test/docs 類型）
- [ ] **GIT-03**: 最終報告包含所有 commit hash 與 push 證據

## v2 Requirements

### 進階功能

- **ADV-01**: AI 自主下單 Stage 3（需保險絲全部就位後才考慮）
- **ADV-02**: Dashboard 美化/響應式設計
- **ADV-03**: 路徑自動遷移工具（OpenClaw → Hermes）

## Out of Scope

| Feature | Reason |
|---------|--------|
| 路徑自動遷移 | 只盤點不改歷史結構，本次只確認不混用 |
| AI 自主下單 | 保險絲仍未全部就位，本次只做保險絲 |
| stock-analysis-tw / taiwan-finance 功能增強 | 非本次範圍 |
| Dashboard 視覺重構 | 只做功能對齊與可讀性，不做全面美化 |
| 歷史 cron 輸出修改 | 歷史紀錄不是現行規則，不改 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 0 | Pending |
| PATH-02 | Phase 0 | Pending |
| PATH-03 | Phase 0 | Pending |
| TRUTH-01 | Phase 1 | Pending |
| TRUTH-02 | Phase 1 | Pending |
| TRUTH-03 | Phase 1 | Pending |
| TRUTH-04 | Phase 1 | Pending |
| FUSE-01 | Phase 2 | Pending |
| FUSE-02 | Phase 2 | Pending |
| FUSE-03 | Phase 2 | Pending |
| FUSE-04 | Phase 2 | Pending |
| FUSE-05 | Phase 2 | Pending |
| TICKET-01 | Phase 3 | Pending |
| TICKET-02 | Phase 3 | Pending |
| TICKET-03 | Phase 3 | Pending |
| TICKET-04 | Phase 3 | Pending |
| TICKET-05 | Phase 3 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| TEST-05 | Phase 4 | Pending |
| GIT-01 | All Phases | Pending |
| GIT-02 | All Phases | Pending |
| GIT-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after roadmap creation*