# ETF_TW 訂單監控與 Fill Detection 修正（P2-2）

## 結論
舊監控鏈最大的問題，不是查得慢，而是查得太自信。

### 主要根因
1. `poll_order_status.py` 依賴不存在的 `adapter.get_trades()`
2. 舊 `~/.hermes/scripts/order_monitor.py` 把 `list_trades()` 過度當成交事實來源
3. fill detection 沒有明確把「broker 查到」與「position delta 推定」分層

---

## 一、已完成修正

### 1. `poll_order_status.py` 已重寫
現在改成：
- 優先用 `adapter.get_order_status(order_id)`
- 若 broker 查不到，且持倉數量變化足以支持，才用 position delta 做保守 filled 推定
- 不再依賴不存在的 `get_trades()`
- 不再把空查詢直接當失敗或成交

### 2. 舊 `order_monitor.py` 已停用
原因：
- 依賴 legacy state
- 硬編碼標的
- 過度信任 `list_trades()`

現在行為：
- 直接輸出停用警告
- 要求改用 ETF_TW 新鏈路

---

## 二、fill detection 新分層

### A 級：broker 明確證據
- `get_order_status(order_id)` 有回應
- 狀態為 `filled` / `partial_filled`
- 有 order_id / broker side 欄位可追

### B 級：position delta 保守推定
當 broker 側查不到，但以下條件成立時，可推定 filled：
- 已知 symbol / action / target quantity
- 有 baseline position quantity
- 後續 position quantity 變化剛好支持這筆訂單已完成

例如：
- buy 1000，baseline 2000 → 現在 3000
- sell 500，baseline 2000 → 現在 1500

### C 級：不可判定
若 broker 查不到，position 也無法形成足夠證據：
- 不可宣稱已成交
- 不可宣稱失敗
- 只能保留為待確認

---

## 三、目前仍存在的限制

### 限制 1：position delta 只能做保守推定
它不適合精細處理：
- 同標的多筆並發委託
- 同時買賣
- 部分成交細節
- 其他非本單造成的持倉變化

### 限制 2：partial fill 仍需更多 broker 細節
目前 callback / reconciliation 已有 partial_filled 支援，但 polling 線若 broker 不回完整 filled_quantity，仍無法完美還原部分成交過程。

### 限制 3：filled_reconciliation 目前偏符號級，不是完整 order-level 對帳
目前 `filled_reconciliation.py` 主要看 symbol 是否進 positions，粒度仍偏粗。

---

## 四、下一步建議
1. 把 `filled_reconciliation` 從 symbol 級提升到 order 級
2. 在 `dashboard` 顯示 fill evidence source：
   - broker_polling
   - broker_callback
   - local_inference
3. 對 local_inference 狀態加明顯標示，避免誤認為 broker 明確確認

---

## 五、正式規則
- broker 查到 > position delta 推定 > 無法確認
- local inference 可以用來避免漏報，但不能假裝成 broker 明確成交回報
- 舊監控鏈若依賴 `list_trades()` 當唯一成交證據，一律視為危險流程
