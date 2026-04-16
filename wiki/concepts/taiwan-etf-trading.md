---
name: 台灣 ETF 現股交易制度
type: concept
tags: [制度, 台股, ETF, T+2, 當沖, 零股]
created: 2026-04-14
updated: 2026-04-16
references: [shioaji-quantity-bug.md, settlement-t2.md, shioaji.md, shioaji-api-limits.md]
sources: [raw/specs/shioaji-official-docs-2026.md]
---

# 台灣 ETF 現股交易制度

## 基本交易單位

| 單位 | 說明 | 適用情境 |
|------|------|----------|
| **整股（張）** | 1 張 = 1000 股 | 一般盤（09:00-13:30）|
| **零股（不足1張）** | 100 股、500 股、800 股等 | 盤後零股（13:40-14:30）|

> ⚠️ **重要**：整股和零股是**兩個不同的交易時段**，政策不同：
> - 一般盤只能交易整股（最小 1000 股）
> - 盤後零股只能交易零股（最小 1 股）
> - ETF_TW 系統若同时具备整股+零股能力，需明確區分時段

## 交易時段

```
09:00 - 13:30  一般現股交易（整股）
13:30 - 13:40  盤後休市
13:40 - 14:30  盤後零股交易（零股）
14:30 以後     收盤，非交易時段
```

## T+2 交割制度

台灣股市採用 **T+2 交割**（Trade Date + 2 Business Days）：

| 日期 | 事件 |
|------|------|
| T 日（交易日） | 買進股票，當日帳面顯示買入成本 |
| T+1 | 券商準備交割款項 |
| T+2 | **款項從帳戶實際扣繳**；股票正式進入集保 |

**關鍵風險**：
- T+2 當日才從帳戶扣款，帳面餘額**不代表實際可用現金**
- 錯誤下單在 T+2 才暴露真實損失
- 變現（賣出）也需 T+2 才能取得款項

## 當日沖銷（當沖）

| 項目 | 內容 |
|------|------|
| 定義 | 同一天內先買進再賣出（或先賣出再買進）同一檔股票 |
| 資格 | 需向券商申請「當日沖銷」資格（當沖戶） |
| 限制 | 未申請當沖者，無法在買進當日賣出 |
| 成本 | 手續費 0.1425% + 證交稅 0.3%（賣出時）|

**TOMO 的限制**：未開通當沖，因此：
- 買進的股票**最早 T+1 才能賣出**（但實際需集保完成，通常 T+2）
- 錯誤買進的 00919 和 006208，在 4/14 當日**無法賣出**

## 永豐金/Shioaji 交易 API

> 完整 API 參考 → [[shioaji]]

### 登入與帳號

| 版本 | 認證方式 | 參數 |
|------|----------|------|
| v1.0+ | Token | `api_key` + `secret_key` |
| v1.0- | 帳號密碼 | `person_id` + `passwd` |

帳號分 `StockAccount`（證券）及 `FutureAccount`（期貨）。模擬模式為 `sj.Shioaji(simulation=True)`。

### 證券下單參數

| 參數 | 值 |
|------|-----|
| `price_type` | LMT / MKT / MKP |
| `order_type` | ROD / IOC / FOK |
| `order_cond` | Cash / MarginTrading / ShortSelling |
| `order_lot` | Common / Odd / IntradayOdd / Fixing |

操作：`place_order()` / `update_order()` / `cancel_order()`，改量**只能減少**。

### API 使用限制

> 完整限制詳見 [[shioaji-api-limits]]

- 頻率：行情 5s/50次、帳務 5s/25次、委託 10s/250次
- 連線：5 連線/person_id、訂閱 200 個、登入 1000次/日
- 流量：依成交額分級 500MB–10GB

### 張股轉換邏輯（Shioaji 特有）

### 股/張轉換邏輯

Shioaji API 的 `Order(quantity=)` 參數：
- **Shioaji 底層**：`quantity` = **張**（lots）
- **ETF_TW Order 物件**：`Order.quantity` = **股**（shares）
- **轉換公式**：`lots = order.quantity // 1000`；零股時 `lots = 1`

```python
# 錯誤示範（已修復）
lots = qty // 1000 if qty >= 1000 else 1  # ❌ 100股→1張

# 正確示範
lots = qty // 1000
if qty % 1000 != 0:
    lots = 1  # 零股券商視為1筆 odd-lot 委托
```

### list_trades() 的限制

```python
api.list_trades()  # 已filled的訂單幾乎回傳空陣列
api.list_orders()  # 可查到已成交/已取消/已拒絕的歷史委託
```

**實務結論**：Fill 監控不應依賴 `list_trades()`，應使用：
1. `api.list_orders()` 輪詢
2. 或持倉 snapshot 差異對比

## 費用結構

| 費用 | 買進 | 賣出 |
|------|------|------|
| 手續費 | 0.1425%（券商可折扣）| 0.1425%（券商可折扣）|
| 證交稅 | 免 | 0.1%（ETF）|
| 總成本（賣出）| ~0.14% | ~0.24% |

## 集保庫存

股票買進後，T+2 才會進入「集保」（集保結算所）。在此之前：
- `list_positions()` 可能仍顯示舊持倉
- 嘗試賣出 → **Error 88「集保庫存不足」**
- 這是正常現象，不是系統故障

---

*本頁依據 TOMO 實際踩坑經驗建立，2026-04-14*
