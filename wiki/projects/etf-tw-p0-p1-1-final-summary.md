# ETF_TW P0 + P1-1 最終摘要（一頁結案報告）

## 結論
這一輪工作的核心，不是優化報酬，而是先把「會讓人真金白銀受傷」的交易敘述與系統行為收斂。

目前已完成：
- P0：交易防呆與真相源校正
- P1-1：台股 ETF 制度知識正式化

---

## 已完成的 5 個 P0 收斂

### 1. 持倉查詢改成誠實分層
之後查持倉固定分成：
1. 本次 live API 直接看到
2. 本次 live API 無法確認
3. 次級資訊（state / summary / memory，明講非 live）
4. 建議下一步

已消除風險：
- 不再把 state / 記憶 / 推測包裝成 live 持倉

### 2. 掛單 / 成交查詢改成保守敘述
已明確寫死：
- `list_orders()` 不存在
- `list_trades()` 查不到，不等於沒下單，也不等於已成交
- `submit_order.status` 不是委託落地證明

已消除風險：
- 不再靠不存在 API 或空值推論亂下結論

### 3. Submit ≠ 委託落地
已修正：
- submit 回應不能直接視為已掛單
- dashboard 改為區分：
  - `submission_attempted`
  - `submit_needs_verification`
  - `submit_verified_hint`
- 只有看到足夠 broker 證據，才可往已提交方向收斂

已消除風險：
- 不再把「送出 submit」寫成「已正式掛單」

### 4. 股 / 張 / order_lot 地雷已收斂
已修正：
- `Order.quantity` 對內一律當「股」
- `Common` 送單 quantity 轉為「張」
- `IntradayOdd` / `Odd` 送單 quantity 以「股」
- 清除「非 1000 倍數一定拒絕」的過時規則

已消除風險：
- 避免再次因 quantity / order_lot 搞混而送出錯單

### 5. ghost order / 假回單治理已落地
已修正：
- ghost 判定寫入 merge 層
- dashboard 不再把 ghost 單算成未完成委託
- reconciliation 會把 ghost 單標成異常
- 現有 state 內殘留 ghost 單已清除

已消除風險：
- 避免再次出現「系統說已掛單，但券商根本沒有」

---

## P1-1 已正式化的制度規則

### 交易時段
- 一般盤：09:00 - 13:30
- 盤後零股：13:40 - 14:30
- 非交易時段：不得假裝可以立即送單

### 整股 / 零股
- 1 張 = 1000 股
- 整股、盤中零股、盤後零股必須分開看
- 不得再用「非 1000 倍數一定非法」這種懶規則回答

### T+2 結算
- 已成交 ≠ 已交割入庫 ≠ 一定可賣
- Error 88 / 集保庫存不足，常見根因是交割尚未完成

### 現金 / 額度
- API 顯示額度，不等於真實現金
- 必須區分真實現金、信用額度、可下單額度

---

## 這輪留下的主要成果

### 已落地檔案
- `~/wiki/projects/etf-tw-remediation-plan.md`
- `~/wiki/projects/etf-tw-remediation-tasklist.md`
- `~/wiki/projects/tw-etf-trading-rules-p1-1.md`
- `~/wiki/projects/etf-tw-p0-p1-1-final-summary.md`

### 已修正的核心區域
- `skills/ETF_TW/SKILL.md`
- `skills/ETF_TW/README.md`
- `skills/ETF_TW/docs/STATE_ARCHITECTURE.md`
- `skills/ETF_TW/docs/BROKER_RECONCILIATION_RULES.md`
- `skills/ETF_TW/docs/AI_DECISION_BRIDGE.md`
- `skills/ETF_TW/scripts/complete_trade.py`
- `skills/ETF_TW/scripts/orders_open_state.py`
- `skills/ETF_TW/scripts/state_reconciliation_enhanced.py`
- `skills/ETF_TW/scripts/adapters/sinopac_adapter.py`
- `skills/ETF_TW/scripts/adapters/sinopac_adapter_enhanced.py`
- `skills/ETF_TW/scripts/market_calendar_tw.py`
- `skills/ETF_TW/dashboard/app.py`

---

## 現在可以怎麼看這套系統

### 可以相信的
- 它現在比之前更不容易亂宣稱「已掛單」
- 它現在比之前更不容易把 state 當 live 真相
- 它現在比之前更不容易在 quantity / order_lot 上出致命錯誤

### 仍要誠實保留的限制
- live API 本身仍可能不完整
- `list_positions()` / `list_trades()` 不是萬能真相機器
- 真正關鍵時，券商 app / web 畫面仍是重要查證來源

---

## 下一步建議
1. P1-2：Shioaji API 真實行為與限制正式化
2. P1-3：錯誤案例庫正式化（Error 88 / 假回單 / state-live 衝突）
3. P2：系統審計與決策引擎修正

---

## 最終一句話
這輪的成果，不是讓系統更會下單；
而是先讓它更不容易用錯誤的自信把人害死。
