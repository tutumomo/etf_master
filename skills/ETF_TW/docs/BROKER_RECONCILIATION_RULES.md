# Broker Reconciliation Rules

## 目的

定義 ETF_TW 在 `submit_response`、`submit_verification`、`broker_polling`、`broker_callback` 多來源同時更新同一 `order_id` 時，如何穩定選出較新、較成熟、較可信的狀態，避免狀態倒退與髒覆蓋。

---

## 真相源與責任分界

- `positions.json` = 持倉真相
- `orders_open.json` = 未終局委託真相
- `portfolio_snapshot.json` / `agent_summary.json` = 衍生展示摘要

---

## 狀態優先序（Status Rank）

| 狀態 | rank |
|---|---:|
| `pending` | 0 |
| `submitted` | 1 |
| `partial_filled` | 2 |
| `filled` | 3 |
| `cancelled` | 3 |
| `rejected` | 3 |

### 規則
1. terminal 狀態（`filled` / `cancelled` / `rejected`）不可被 non-terminal 覆蓋。
2. `partial_filled` 不可被 `submitted` 覆蓋。

---

## 時間優先序（Timestamp Precedence）

### 欄位
- `event_time`：broker 事件時間（若可得）
- `observed_at`：本地收到/寫入時間

### 規則
1. 同 rank 時，優先比較 `event_time`
2. 若缺 `event_time`，退回比較 `observed_at`
3. 較新的時間優先

---

## 券商序號優先序（Broker Sequence Precedence）

### 欄位
- `broker_seq`

### 規則
當 status rank 與時間相同時：
- 較大的 `broker_seq` 優先

---

## 來源優先序（Source Priority）

| source_type | priority |
|---|---:|
| `broker_callback` | 4 |
| `broker_polling` | 3 |
| `submit_verification` | 2 |
| `submit_response` | 1 |
| `local_inference` | 0 |

### 規則
當 rank、時間、seq 都無法分出勝負時，使用來源優先序。

---

## Partial Fill 規則

### 欄位
- `filled_quantity`
- `remaining_quantity`
- `total_quantity`（若可得）

### 規則
1. `filled_quantity` 只能前進，不可倒退
2. 只有在明確有 `total_quantity` 時，才自動重算 `remaining_quantity = total_quantity - filled_quantity`
3. 若缺少 `total_quantity`，保留顯式給定的 `remaining_quantity`，避免錯把 `quantity` 當成 total quantity

---

## Metadata Contract

### callback / normalizer row
應盡量包含：
- `source_type = broker_callback`
- `raw_status`
- `observed_at`
- `event_time`（若可得）
- `broker_seq`（若可得）

### polling row
應包含：
- `source_type = broker_polling`
- `raw_status`
- `observed_at`
- partial fill 時可同步寫入 `fills_ledger.json`

### submit verification row
應包含：
- `source_type = submit_verification`
- `raw_status`
- `observed_at`

---

## 當前實作狀態

已落地：
- precedence helper
- status rank
- timestamp precedence
- broker seq precedence
- source priority
- partial fill monotonicity 基礎護欄
- callback / polling / submit metadata contract
- fills ledger state IO
- callback partial fill → fills ledger sync
- polling partial fill → fills ledger sync
- filled reconciliation report helper
- filled reconciliation refresh hook
- dashboard health 可承接 filled reconciliation warning

待補：
- 更完整 broker event timestamp 對齊
- submit_response metadata contract
- broker source priority 文檔持續對齊更多 broker adapter
