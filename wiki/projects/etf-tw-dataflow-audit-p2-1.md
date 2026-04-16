# ETF_TW 資料流審計（P2-1）

## 結論
ETF_TW 目前不是單一資料源系統，而是四層結構：
1. broker live API
2. instance state
3. dashboard view model
4. agent 對外回答

真正的問題不是「檔案太多」，而是這四層容易被誤說成同一層。

---

## 一、四層角色分工

### Layer A：broker live API
用途：
- 當次查詢券商側可見資訊
- 取得委託、持倉、餘額等即時證據

限制：
- 不是萬能真相機器
- `list_positions()` / `list_trades()` 可能不完整
- 查不到不能直接推出失敗或成交

正式角色：
- 對外回答時的優先查證層

---

### Layer B：instance state
核心檔案：
- `positions.json`
- `orders_open.json`
- `portfolio_snapshot.json`
- `agent_summary.json`
- `filled_reconciliation.json`

用途：
- 系統內部落盤
- 對帳
- dashboard 載入
- workflow 串接

限制：
- 不是自動等於 live truth
- 可能殘留 ghost order
- 可能是 snapshot，不是當下券商狀態

正式角色：
- system-of-record / reconciliation 層
- 不是對外回答的唯一真相層

---

### Layer C：dashboard
關鍵檔案：
- `dashboard/app.py`

用途：
- 將 state 組裝成使用者可讀畫面
- 建立 view model、warning、reconciliation 訊號

限制：
- dashboard 會做 fallback
- 例如 `positions.json` 空時，可能回退到 `portfolio_snapshot`
- 所以 dashboard 是展示層，不是原始證據層

正式角色：
- 使用者感知層 / 展示層

---

### Layer D：agent 回答層
用途：
- 用白話向使用者說明

限制：
- 最容易犯的錯，就是把 A/B/C 三層混講成單一事實

正式角色：
- 誠實翻譯層
- 必須標註：本次 live 看到 / 無法確認 / 次級資訊

---

## 二、目前實際資料流

### 持倉鏈
broker live API → `positions.json` → dashboard position view → agent 回答

### 掛單鏈
submit / callback / polling → `orders_open.json` → dashboard open orders / warnings → agent 回答

### 成交補強鏈
callback / polling / fill facts → `fills_ledger.json` → `filled_reconciliation.json` → dashboard reconciliation warnings

### 資產快照鏈
positions + market cache + account → `portfolio_snapshot.json` → dashboard fallback / KPI

---

## 三、目前的主要風險點

### 風險 1：dashboard fallback 可能被誤認成 live truth
在 `dashboard/app.py` 中，當 `positions.json` 空時，會 fallback 到 `portfolio_snapshot`。

風險：
- 對使用者來說畫面仍會有數字
- 但那不是 broker live query 本身

建議：
- dashboard 顯示層加註 source label
- agent 回答時不得把 fallback 當成 broker 即時查證

### 風險 2：orders_open 是 workflow state，不等於券商必然存在
即使現在 ghost order 已治理，仍不能把 `orders_open.json` 本身講成券商真相。

### 風險 3：agent 很容易把 state / dashboard / live API 混成一句話
這是之前最致命的錯誤來源。

---

## 四、正式分工規則

### 對外回答時
- 優先：broker live API / 券商畫面
- 次級：instance state
- 展示：dashboard
- 背景：summary / memory / wiki

### 對內系統時
- instance state 是正式落盤層
- dashboard 是 state 的展示與 fallback 組裝層
- reconciliation 是 state 的健康檢查層

---

## 五、建議後續修正
1. dashboard 顯示每塊資料的 source label
2. agent 查詢模板固定帶 source 分層
3. 將 fallback 狀態明確標記為 fallback，不與 live 混淆
