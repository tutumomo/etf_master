# Daily Submit Quota Design

## Goal

在現有「交易閾值與安全紅線」之下，新增兩個面向 live trading 的每日交易配額限制：

- `daily_max_buy_submits`
- `daily_max_sell_submits`

預設值皆為 `2`，且採用「只要委託成功送出到 broker 掛單就算 1 次」的定義，不以成交結果為準。

## Why

現有 Safety Redlines 主要約束單筆風險與當日整體損益風險，但仍缺少對智能體「出手頻率」的硬性上限。若未來開放智能體下單，最常見的失控模式不一定是單筆過大，而是短時間內多次嘗試下單。

這個配額限制的目的不是評估策略品質，而是直接限制 live submit 的日內操作次數，讓系統在最壞情況下也只會產生有限次真實委託。

## Product Semantics

### New Settings

在 `safety_redlines.json` 新增：

```json
{
  "daily_max_buy_submits": 2,
  "daily_max_sell_submits": 2
}
```

### Counting Rule

- 僅統計 **live submit**。
- 僅在委託已成功送達 broker、系統取得成功提交結果後才計數。
- 不論後續是未成交、部分成交、全部成交、取消、撤單，次數都不返還。
- 買入與賣出分開計數。
- 每日日期切換時自動歸零。

### Non-Goals

- 不統計 preview / paper / 模擬流程。
- 不按成交筆數、成交股數、成交金額計數。
- 不做「取消後退回配額」。

## Architecture

### Configuration State

現有 `safety_redlines.json` 繼續作為設定來源，新增兩個 quota fields。這讓 Dashboard、Gate、Live SOP 都從同一份 operator-facing 設定讀值。

### Runtime Counter State

新增獨立狀態檔：

`instances/<agent_id>/state/daily_order_limits.json`

建議格式：

```json
{
  "date": "2026-04-17",
  "buy_submit_count": 1,
  "sell_submit_count": 0,
  "last_updated": "2026-04-17T17:40:00+08:00"
}
```

這個檔案不與 `daily_pnl.json` 混用，因為兩者職責不同：

- `daily_pnl.json`：日損益 baseline / 熔斷
- `daily_order_limits.json`：日內 live submit 配額計數

## Enforcement Flow

### Read / Block Layer

`pre_flight_gate.py` 新增 quota 檢查：

- `side == "buy"` 時，若 `buy_submit_count >= daily_max_buy_submits`，回傳 fail
- `side == "sell"` 時，若 `sell_submit_count >= daily_max_sell_submits`，回傳 fail

建議 failure reason：

- `daily_buy_submit_limit_reached`
- `daily_sell_submit_limit_reached`

這樣 quota 屬於與 redlines 同層級的 hard stop，但本質上是日內配額，不是單筆金額限制。

### Mutation Layer

`live_submit_sop.py` 在 **broker submit 成功返回後** 遞增計數：

- buy 成功送出 → `buy_submit_count += 1`
- sell 成功送出 → `sell_submit_count += 1`

若送單前就被 gate 擋下，或 submit 本身失敗，則不計數。

## Dashboard UX

在既有「交易閾值與安全紅線」卡片新增兩個欄位：

- `每日可下單買入次數`
- `每日可下單賣出次數`

同時顯示當日使用狀態，例如：

- `今日買入已送出：1 / 2`
- `今日賣出已送出：0 / 2`

Tooltip 建議：

- 買入：只要成功送出一筆真實買入委託，就扣 1 次，不看成交與否
- 賣出：只要成功送出一筆真實賣出委託，就扣 1 次，不看成交與否

## Error Handling

### Fail-Closed vs Fail-Open

這個限制應採 **fail-closed** 還是 **fail-open**，需要一致策略。

建議：

- `safety_redlines.json` 缺失：沿用預設值
- `daily_order_limits.json` 缺失：自動初始化當日空計數
- `daily_order_limits.json` 損毀且無法解析：保守起見應 block live submit，避免因狀態損毀導致配額失效

這一點和現行 `pre_flight_gate.py` 對 safety redlines 的非阻斷 fallback 不同，因為 quota 是 live unlock 後的核心保護欄，風險更直接。

## Tests

至少要新增：

1. buy quota 未達上限時可通過
2. buy quota 達上限時被阻擋
3. sell quota 達上限時被阻擋
4. submit 成功後正確遞增對應 side 計數
5. submit 失敗時不遞增
6. 跨日自動重置計數
7. Dashboard API 可正確讀寫兩個 quota 欄位

## Recommendation

這個設計合理，且與現有架構相容。推薦做法是：

- 設定值放在 `safety_redlines.json`
- 計數值獨立放在 `daily_order_limits.json`
- gate 負責阻擋
- live SOP 負責在成功送單後計數
- Dashboard 在同一卡片中呈現設定與當日使用量

這樣可以保持 operator 心智模型簡單，同時避免把「設定」與「當日執行狀態」混成同一份檔案。
