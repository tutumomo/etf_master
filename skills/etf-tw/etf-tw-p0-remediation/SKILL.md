---
name: etf-tw-p0-remediation
description: ETF_TW 交易致命錯誤 P0 收斂流程：持倉/掛單誠實分層、submit≠落地、股張/order_lot、ghost order 治理
---

# ETF_TW P0 Remediation

## 何時使用
- 系統剛發生真實交易事故後
- 需要全面收斂 ETF_TW 的交易敘述與下單風險
- 使用者明確要求「不要再靠幻覺回答」「把爛攤子收乾淨」

## 目標
先修會害死人、害使用者誤判的問題，再談知識整理或決策優化。

---

## P0 五步驟

### P0-1 持倉查詢誠實分層
固定回答格式：
1. 本次 live API 直接看到
2. 本次 live API 無法確認
3. 次級資訊（state / summary / memory，必須明講非 live）
4. 建議下一步（必要時請使用者提供券商 app / web 畫面）

**禁止**：
- 把 state / memory / summary 說成 live 持倉
- 因為之前下過單，就推論現在一定持有
- live API 異常時自行挑一個版本當真相

**掃描關鍵字**：
- `持倉真相源`
- `positions.json`
- `broker live API 優先於 state，但不足時不能硬判為唯一真相`
- `100% 準確`

### P0-2 掛單 / 成交查詢保守化
**原則**：
- `list_orders()` 不存在，不要幻想 API
- `list_trades()` 查不到，不等於沒下單、不等於已成交
- `submit_order.status` 只是 submit 階段訊號，不足以單獨證明委託落地

**掃描關鍵字**：
- `查無此單`
- `list_trades() 回傳空`
- `已成交`
- `掛單確認`
- `成功進券商`

### P0-3 Submit ≠ 委託落地
**必查檔案**：
- `scripts/complete_trade.py`
- `dashboard/app.py`
- `references/live-trading-sop.md`

**必修原則**：
- 不能因 `submitted/pending` 就當成 landed
- 至少要有其一才可較強地宣稱落地：
  - `verified=True`
  - `broker_order_id` 存在
  - 可靠持倉證據
  - 真正 `filled/partial_filled`
- dashboard 要區分：
  - `submission_attempted`
  - `submit_needs_verification`
  - `not_submitted`

### P0-4 股/張 / order_lot 地雷
**核心原則**：
- `Order.quantity` 對內一律視為「股」
- `Common`：送單 quantity 應轉成「張」
- `IntradayOdd` / `Odd`：送單 quantity 以「股」
- 不可用過時規則說「非 1000 倍數一定拒絕」
- 零股是否支援，以當前 adapter 實作為準

**重點檔案**：
- `scripts/adapters/sinopac_adapter.py`
- `scripts/adapters/sinopac_adapter_enhanced.py`
- 任何寫 `lots = qty // 1000 if qty >= 1000 else 1` 的地方

**危險訊號**：
- 註解說 Common=1000股，但程式把股數直接塞給 `quantity`
- 技能文件仍寫 `quantity must be 1000 的倍數`

### P0-5 Ghost order / 假回單治理
**Ghost 判定**（可直接寫成程式規則）：
- `source_type == submit_verification`
- `verified == false`
- `order_id` 空
- `broker_order_id` 空
- `status in {pending, submitted}`

符合以上 → 視為 ghost order，從 `orders_open.json` 清除，不得列為 open order，也不得在 dashboard 顯示成未完成委託。

**必修檔案**：
- `scripts/orders_open_state.py`
- `scripts/state_reconciliation_enhanced.py`
- `dashboard/app.py`
- `instances/<agent_id>/state/orders_open.json`

---

## 後續延伸（這次補上的 P2 教訓）

### P2-1 資料流審計：四層一定要分清楚
- `broker live API` = 對外回答時的優先查證層
- `instance state` = 系統內部落盤 / 對帳層（system-of-record），不是對外唯一 live 真相
- `dashboard` = 展示 / fallback 組裝層
- `agent response` = 誠實翻譯層，必須標示「本次 live 看到 / 無法確認 / 次級資訊」
- 典型誤區：把 dashboard fallback 或 `orders_open.json` 直接講成券商事實

### P2-2 訂單監控 / fill detection 修正要點
- `poll_order_status.py` 舊版依賴不存在的 `adapter.get_trades()`；正式修法是改用 `adapter.get_order_status(order_id)`
- broker 查不到時，不能直接說失敗或成交；若要補強，只能用 `position delta` 做保守 filled 推定
- fill detection 證據分級：
  1. broker 明確證據（最佳）
  2. position delta 推定（次級、需標示 `local_inference`）
  3. 無法確認（不得硬判）
- 舊 `~/.hermes/scripts/order_monitor.py` 已確認屬危險 legacy 鏈路：依賴 legacy state + 過度信任 `list_trades()`；最佳做法是直接停用並導向 `ETF_TW/scripts/poll_order_status.py`

### 交易時段 / 市場日曆一致性
- `market_calendar_tw.py` fallback 不能只覆蓋 09:00-13:30；必須把 13:40-14:30 的盤後零股納入，否則會和 `trading_hours_gate.py` 打架
- fallback session 建議至少明確區分：`regular` / `after_hours` / `closed`

**必修檔案**：
- `scripts/orders_open_state.py`
- `scripts/state_reconciliation_enhanced.py`
- `dashboard/app.py`
- `instances/<agent_id>/state/orders_open.json`

### P0 總驗收補充（2026-04）
- `market_calendar_tw.py` 的 weekday fallback 不能只覆蓋 09:00-13:30；必須把 13:40-14:30 盤後零股納入，否則會和 `trading_hours_gate.py` 打架
- `etf-tw-live-query` 若要提 `list_orders()`，只保留文字警告，不要再留錯誤示範 code block，避免 agent 把示範錯碼當可執行範本
- `sinopac_adapter.py` / `sinopac_adapter_enhanced.py` 必須再次核對 `Common` 與 `IntradayOdd/Odd` 的 quantity 語境：
  - `Common` → quantity 送「張」
  - `IntradayOdd` / `Odd` → quantity 送「股」
- 若掃描到舊句 `broker API 是唯一真相源`，要改成：broker live API 優先於 state，但不足時不能硬判為唯一真相

---

## 建議執行順序
1. 搜尋活文件與活程式（先不要管歷史 cron output / changelog）
2. 先修技能與文件，防止 agent 繼續亂講
3. 再修核心程式邏輯（submit / order_lot / ghost merge）
4. 直接清除當前 state 裡的 ghost order 殘留
5. 做最小驗證：`py_compile` + 重新搜尋關鍵錯誤語句

---

## P2 延伸（這輪實戰新增）

### P2-1 資料流分層審計
當 P0 收斂後，下一步要正式畫清楚 4 層：
1. broker live API
2. instance state
3. dashboard view model
4. agent 對外回答

**原則**：
- live API = 優先查證層
- instance state = system-of-record / reconciliation 層
- dashboard = 展示 / fallback 層
- agent = 誠實翻譯層

**新增教訓**：
- dashboard 有 fallback（例如 positions 空時回退 portfolio_snapshot），畫面有數字 ≠ broker live truth
- 最好在 overview API 與前端直接加 `data_sources` / `is_fallback`，不要只靠口頭說明

### P2-2 訂單監控 / fill detection 深修
**危險訊號**：
- 監控腳本呼叫不存在的 `adapter.get_trades()`
- 舊 cron / 舊 monitor 把 `list_trades()` 過度當成交事實來源
- 空查詢直接推論失敗或已成交

**修正原則**：
- 優先用 `adapter.get_order_status(order_id)`
- broker 查不到時，若持倉 quantity delta 足夠支持，才用 `local_inference` 保守推定 filled
- `local_inference` 不得假裝成 broker 明確成交回報
- 舊版 `~/.hermes/scripts/order_monitor.py` 這類 legacy 監控若依賴 list_trades 當唯一成交證據，應直接停用或明確標成 deprecated

### P2-2b filled_reconciliation 升級
舊版只有 symbol 級：`unreconciled_symbols`

**應升級為 order 級，至少新增：**
- `unreconciled_orders`
- `unreconciled_order_count`
- 每筆帶：`order_id` / `symbol` / `status` / `filled_quantity` / `position_quantity` / `issue` / `source_type`

**向後相容**：
- 保留 `unreconciled_symbols` / `unreconciled_count`，避免 dashboard / tests 立刻炸掉

### P2-3 決策層審計
**要查的 3 件事**：
- preview quantity 是否只是 placeholder（例如固定 100）
- reasoning 是否真對齊 score path，而不是事後合理化
- consensus 是否只是 preview 治理，而非完整 live execution gate

**這輪真 bug**：
- `generate_ai_agent_response.py` 曾有 confidence 降級邏輯錯誤：low 會被誤升成 medium
- 正確降級：high→medium、medium→low、low 保持 low

---

## 最小驗證清單
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m py_compile \
  scripts/complete_trade.py \
  scripts/orders_open_state.py \
  scripts/state_reconciliation_enhanced.py \
  scripts/adapters/sinopac_adapter.py \
  scripts/adapters/sinopac_adapter_enhanced.py \
  dashboard/app.py
```

再用搜尋驗證這些錯誤語句是否已清掉：
- `positions.json = 持倉真相`
- `orders_open.json = 未終局委託真相`
- `list_trades() 回傳空 -> 根本沒送進券商`
- `submitted 表示成功進券商`
- `quantity must be 1000 的倍數`
- `✅ 已正式掛單`

---

## 注意事項
- 歷史輸出（cron output / graph report / changelog）可先不動，先修活規則
- 若 live API 本身不可靠，也要誠實承認「無法確認」
- 這套流程的目的不是把系統說得漂亮，而是避免再次讓使用者因錯誤敘述承受真實資金風險
