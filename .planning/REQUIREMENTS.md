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
- [ ] **TRUTH-05**: 決策控制台二條建議決策機制必須落地可用（audit AI decision bridge 現況，確認 request→response→consensus 全鏈通暢，dashboard 可正確顯示建議）

### 交易保險絲 (FUSE)

- [ ] **FUSE-01**: sizing policy 與 pre-flight gate 單一路徑化（買賣皆適用，不因路徑不同而雙標）
- [ ] **FUSE-02**: 交易前阻擋條件一致化（quantity>0、限價>0、集中度、單筆上限、交易時段、張/股單位、賣出庫存檢查）
- [ ] **FUSE-03**: submit 後必須進入落地驗證流程（list_trades + positions/其他佐證）
- [ ] **FUSE-04**: 風控限制可準確擋單（單元測試證明：超限被擋、超庫存被擋、submit成功但未落地不被誤報成功）
- [ ] **FUSE-05**: sizing_engine_v1 正式計算規則（輸入：現金、集中度上限、單筆上限、風險溫度；輸出：建議股數、限制原因、是否可下單）
- [ ] **FUSE-06**: 交易閾值可設定（現金百分比或其他指標），閾值觸發時可在持倉快照區塊直接下單買入/賣出（仍受 pre-flight gate 把關）

### 持倉交易票據 (TICKET)

- [x] **TICKET-01**: 持倉主列保持乾淨，只留「交易」入口按鈕
- [x] **TICKET-02**: 交易票據放在展開層（drawer/inline detail），不在主列塞表單
- [x] **TICKET-03**: preview → confirm → submit 三段式（預覽通過後才顯示確認字串 + 送出按鈕）
- [x] **TICKET-04**: 維持人工確認，不允許預覽即送單
- [x] **TICKET-05**: 送單仍受 pre-flight 與權限控制（不受 auto-preview 限制，但受 sizing + 風控限制）
- [x] **TICKET-06**: Dashboard 區塊可設定為可摺疊收起（使用者可依需求展開/收合，避免資訊過載）
- [x] **TICKET-07**: 初次使用者泡泡文字說明（tooltip/onboarding hints），讓不熟悉股市的新手能理解每個區塊的意義

### 回歸測試 (TEST)

- [ ] **TEST-01**: 單位與 odd-lot 回歸案例（Common 張/IntradayOdd 股）
- [ ] **TEST-02**: list_trades 空回應語義回歸案例
- [ ] **TEST-03**: submit≠落地回歸案例
- [ ] **TEST-04**: 持倉票據 preview/confirm/submit 流程回歸案例
- [ ] **TEST-05**: sizing 政策變更可生效回歸案例

### 版本憑證 (GIT)

- [x] **GIT-01**: 每階段必須 commit，最終必須 push 到 https://github.com/tutumomo/etf_master
- [x] **GIT-02**: commit 訊息包含範圍與目的（fix/refactor/test/docs 類型）
- [ ] **GIT-03**: 最終報告包含所有 commit hash 與 push 證據

## v2 Requirements

### 進階功能

- **ADV-01**: AI 自主下單 Stage 3（需保險絲全部就位後才考慮）
- **ADV-02**: Dashboard 美化/響應式設計
- **ADV-03**: 路徑自動遷移工具（OpenClaw → Hermes）
- **ADV-04**: K線圖時間週期切換（日線/月線/季線/年線），在盤感輔助層「詳情圖表」中提供選擇
- **UI-INTEGRATE**: Dashboard 持倉與關注區塊優化整合，包含合併盤感、預設 100 股、動態買賣邏輯

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
| PATH-01 | Phase 00 | Pending |
| PATH-02 | Phase 00 | Pending |
| PATH-03 | Phase 00 | Pending |
| TRUTH-01 | Phase 01 | Pending |
| TRUTH-02 | Phase 01 | Pending |
| TRUTH-03 | Phase 01 | Pending |
| TRUTH-04 | Phase 01 | Pending |
| TRUTH-05 | Phase 01 | Pending |
| FUSE-01 | Phase 02 | Pending |
| FUSE-02 | Phase 02 | Pending |
| FUSE-03 | Phase 02 | Pending |
| FUSE-04 | Phase 02 | Pending |
| FUSE-05 | Phase 02 | Pending |
| FUSE-06 | Phase 02 | Pending |
| TICKET-01 | Phase 03 | Complete |
| TICKET-02 | Phase 03 | Complete |
| TICKET-03 | Phase 03 | Complete |
| TICKET-04 | Phase 03 | Complete |
| TICKET-05 | Phase 03 | Complete |
| TICKET-06 | Phase 03 | Complete |
| TICKET-07 | Phase 03 | Complete |
| TEST-01 | Phase 04 | Pending |
| TEST-02 | Phase 04 | Pending |
| TEST-03 | Phase 04 | Pending |
| TEST-04 | Phase 04 | Pending |
| TEST-05 | Phase 04 | Pending |
| GIT-01 | All Phases | Complete |
| GIT-02 | All Phases | Complete |
| GIT-03 | Phase 04 | Pending |
| UI-INTEGRATE | Phase 07 | Complete |

**Coverage:**
- v1 requirements: 30 total
- v2 requirements: 5 total
- Mapped to phases: 31
- Unmapped: 4 (ADV-01...04)

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-16 — added UI-INTEGRATE*