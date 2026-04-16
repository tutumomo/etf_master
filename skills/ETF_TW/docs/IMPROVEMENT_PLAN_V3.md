# ETF_TW Improvement Plan v3.1

## 目的

在完成 state architecture 收斂、dashboard refresh 修復、orders_open / callback / polling / fills ledger / filled reconciliation 主幹之後，下一階段改造要從「功能散點補洞」進一步收斂成 **幾條清楚的工程主線**。

這份重整版計劃的目的不是重述歷史，而是：
- 反映這兩天已完成的實作真相
- 把後續工作改成更貼近現況的主線結構
- 避免舊版線性 P1/P2/P3 已完成，但後續工作仍混在同一段造成閱讀負擔

---

## 這兩天已完成的核心成果

### 1. Orders Open / Broker Reconciliation 主幹已建立
- `orders_open.json` 契約與 status lifecycle 已穩定
- submit / polling / callback 已開始收斂到同一 state machine
- submit response ≠ order landed 的護欄已建立
- precedence helper 已落地
- status rank / timestamp precedence / source priority / broker seq precedence 已建立

### 2. Partial Fill 鏈已從概念走到可用骨架
- partial fill status normalization
- partial fill quantity monotonicity guard
- partial fill 不直接變完整持倉
- partial fill 可寫入 fill facts / `fills_ledger.json`
- callback / polling partial fill → fills ledger 已接通

### 3. Filled Reconciliation 鏈已成形
- filled fact 與 positions truth 的責任邊界已定義
- unreconciled filled symbols helper 已建立
- reconciliation report helper 已建立
- reconciliation report state IO 已建立
- refresh hook 已建立
- dashboard health / overview / template / global banner 已接上

### 4. Dashboard / State / Warning 顯示層明顯強化
- health summary 已能吃 reconciliation warning
- overview API 已暴露 filled reconciliation block
- overview template 已顯示 filled reconciliation 區塊
- global banner / refresh 後摘要提示已接上 unreconciled fills

### 5. Market Calendar 問題已被正式識別
- 已確認「只靠 weekday + time」會誤判休市日
- 已建立最低可用 `market_calendar_tw.py` helper 與 test-first 驗證
- 但目前僅屬最低可用層，不列為當前最高優先主線

---

## 新版主線規劃

---

## 主線 A：Filled / Positions Reconciliation Close-the-loop

### 目標
從「能發現 filled 與 positions 尚未對齊」走到「能穩定完成對齊與清警訊」。

### 當前狀態
**IN_PROGRESS**

### 已完成
- [x] filled fact 與 positions truth 邊界定義
- [x] `filled_reconciliation.py`
- [x] unreconciled symbols helper
- [x] reconciliation report helper
- [x] reconciliation report state IO
- [x] refresh hook
- [x] dashboard health / overview / template / global banner 接線

### 待做
- [ ] 定義 filled 後 broker positions 對齊的正式完成條件
- [ ] 補 positions 更新後 snapshot / summary 對齊 helper
- [ ] 補 unreconciled 狀態的清除條件與時機
- [ ] 規劃 broker 延遲 / sync failure / drift 的分級 warning
- [ ] 視需要補 `filled_reconciliation.json` 與 dashboard refresh summary 更細語意

### 建議下一步
1. `filled_reconciliation.py` 加入更完整的 reconciliation action / status classifier
2. 補 `positions` 對齊成功後 warning 清除測試
3. 視需要把 reconciliation count 納入 agent summary

---

## 主線 B：TW Market Calendar / Holiday Detection

### 目標
讓交易日 / 休市判斷不再只靠 weekday + time 猜測，避免連假、補假、颱風停市等誤判。

### 當前狀態
**MINIMUM VIABLE ONLY**

### 已完成
- [x] 問題識別與 test-first 驗證
- [x] `market_calendar_tw.py` 最低可用 helper
- [x] `get_today_market_status()` / `is_tw_market_open_now()`
- [x] dashboard overview 可暴露 `market_calendar_status`
- [x] 若 market calendar 與 naive weekday/time 矛盾，可進 warning

### 待做
- [ ] 定義 `market_calendar_tw.json` 最低欄位契約
- [ ] 建立 calendar state / update source
- [ ] dashboard / auto_trade_state / health 全面改為 calendar-first
- [ ] refresh / UI 顯示 holiday reason
- [ ] 規劃 fallback 缺資料時的 warning 級別

### 註記
這條線目前先停在最低可用版，不是當前最高優先功能。

---

## 主線 C：Submit / Verification / Polling / Callback Contract Completion

### 目標
把四條來源路徑都補成同級、可比較、可審核的正式 contract。

### 當前狀態
**MOSTLY DONE, NEEDS FINISHING**

### 已完成
- [x] submit verification metadata contract
- [x] polling metadata contract
- [x] callback metadata contract
- [x] precedence helper
- [x] timestamp precedence
- [x] source priority
- [x] broker seq precedence
- [x] partial fill monotonicity guard
- [x] `BROKER_RECONCILIATION_RULES.md`

### 待做
- [ ] submit_response metadata contract 正式化
- [ ] 更完整 broker event timestamp / seq / source priority 文檔收斂
- [ ] 視需要補更多 terminal / stale edge case

### 建議下一步
- 將 `submit_response` 納入與 `submit_verification` 同級的 row metadata contract

---

## 主線 D：Partial Fill / Fills Ledger / Portfolio Boundary

### 目標
把 partial fill 從單純 state 欄位，升級成正式的 fill facts 與持倉邊界管理鏈。

### 當前狀態
**SOLID BASE BUILT**

### 已完成
- [x] fills ledger 最低欄位契約
- [x] `fills_ledger.py`
- [x] fills ledger state IO
- [x] callback partial fill → fills ledger sync
- [x] polling partial fill → fills ledger sync
- [x] partial fill 不直接進 `positions.json`
- [x] partial fill 不直接變 snapshot holdings
- [x] partial fill summary boundary 已建立

### 待做
- [ ] 規劃 filled 後 fills ledger / positions / snapshot 的最終一致性閉環
- [ ] 視需要補 fills history / fill event trace 顯示
- [ ] 視需要補 fill logger 與 fills ledger 對齊

---

## 主線 E：Dashboard / Summary / Docs Consolidation

### 目標
把這兩天長出來的規則與顯示層整理成正式、可維護的體系，不讓規則只存在程式與對話裡。

### 當前狀態
**IN_PROGRESS**

### 已完成
- [x] dashboard health 可顯示 reconciliation warning
- [x] overview API 已暴露 filled reconciliation block
- [x] overview template 已顯示 filled reconciliation 區塊
- [x] global banner / refresh 後摘要提示已接上 unreconciled fills
- [x] `BROKER_RECONCILIATION_RULES.md`
- [x] changelog / tasks / plan 多輪同步

### 待做
- [ ] 視需要把 filled reconciliation count 接入 agent summary
- [ ] 視需要新增 `FILLS_LEDGER.md` / `ORDER_LIFECYCLE.md`
- [ ] market calendar 規則文件化
- [ ] dashboard refresh summary / status center 的語意再收斂

---

## 目前不建議提高優先的事項

以下暫不提升優先級：
- 多券商深度擴充
- 新聞 / 情緒 / 情報擴充
- decision engine 更深優化
- live auto-trading guardrails 的實際啟用
- 大量 UI 美化

原因：目前最重要的仍是先把：
- broker lifecycle
- fills / positions truth boundary
- reconciliation
- dashboard state consistency

這幾條主幹鎖穩。

---

## 建議執行順序（重整版）

### 第一優先
1. 主線 A：Filled / Positions Reconciliation Close-the-loop
2. 主線 C：Submit / Verification / Polling / Callback Contract Completion

### 第二優先
3. 主線 D：Partial Fill / Fills Ledger / Portfolio Boundary 深化
4. 主線 E：Dashboard / Summary / Docs Consolidation

### 暫維持最低可用
5. 主線 B：TW Market Calendar / Holiday Detection

---

## 一句話總結

ETF_TW 下一階段不是追求更多功能，而是：

> 把 callback / polling / fills / positions / dashboard 這條交易狀態鏈，補成可信、可對齊、可維護的正式主幹。
