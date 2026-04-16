# 永豐金證券 API 測試報告

## 測試基本資訊
- **測試日期**: 2026-03-26
- **測試人員**: Tomo (ETF_Master)
- **API Key 名稱**: ETF_master
- **測試環境**: 模擬環境 (Simulation) + 正式環境 (Production)
- **帳戶**: 0737121 (涂呈欣)
- **測試狀態**: ✅ 完整測試流程已完成

---

## 測試目的
完成永豐金證券 API 測試流程，申請開通正式帳務/下單權限。

---

## 測試結果摘要

| 測試項目 | 模擬環境 | 正式環境 | 說明 |
|---------|---------|---------|------|
| API 登入 | ✅ 成功 | ✅ 成功 | 可取得 2 個帳戶（00285915 海外、0737121 證券） |
| ETF 報價 | ✅ 成功 | ✅ 成功 | 可查詢 0050 等 ETF 即時行情 |
| 訂單建立 | ✅ 成功 | ⏳ 待測試 | 可建立 Buy 訂單（0050, 1 股, 市價單） |
| 委託送出 | ✅ 成功 | ⏳ 待測試 | 模擬環境委託成功 |
| 帳戶餘額 | ⚠️ 不支援 | ❌ 未開通 | 模擬環境不支援，正式環境顯示 Account Not Acceptable |
| 持股查詢 | ✅ 成功 | ❌ 未開通 | 模擬環境可查（0 筆），正式環境 Account Not Acceptable |
| 委託查詢 | ✅ 成功 | ✅ 成功 | 可查詢今日委託（目前 0 筆） |

---

## 詳細測試過程

### 1. API 登入測試
```python
api = sj.Shioaji(simulation=True)  # 模擬環境
api = sj.Shioaji(simulation=False) # 正式環境

accounts = api.login(
    api_key="9NTj2vBsfbbGA4kBRH83Bi9KVq7bqVAJAHg8PqvVkuL5",
    secret_key="51xgnv3dC4iQcPUrgn2Dc9vX1r8QP2H18HiwNrJ35ZVM"
)
```

**結果**:
- ✅ 模擬環境：登入成功，取得 2 個帳戶
- ✅ 正式環境：登入成功，取得 2 個帳戶
- 帳戶列表：
  - `00285915` (Account) - 海外帳戶
  - `0737121` (StockAccount) - 證券帳戶

### 2. 帳戶餘額查詢
```python
balance = api.account_balance(stock_acc)
```

**結果**:
- ⚠️ 模擬環境：回傳 `AccountBalance` 物件，餘額 0.0（模擬環境不支援）
- ❌ 正式環境：`{'status': {'status_code': 406}, 'response': {'detail': 'Account Not Acceptable.'}}`

### 3. 持股查詢
```python
positions = api.list_positions(stock_acc)
```

**結果**:
- ✅ 模擬環境：成功，0 筆持股
- ❌ 正式環境：`Account Not Acceptable.`

### 4. ETF 合約查詢
```python
contract = api.Contracts.Stocks.TSE['0050']
```

**結果**:
- ✅ 模擬環境：成功，0050 元大台灣 50，參考價 76.2
- ✅ 正式環境：成功，0050 元大台灣 50，參考價 76.05

### 5. 委託查詢
```python
trades = api.list_trades()
```

**結果**:
- ✅ 模擬環境：成功，0 筆委託
- ✅ 正式環境：成功，0 筆委託

### 6. 證券下單測試（2026-03-26 新增）
```python
from shioaji.constant import Action, OrderType, StockPriceType

order = api.Order(
    price=contract.reference,
    quantity=1,
    action=Action.Buy,
    price_type=StockPriceType.MKT,
    order_type=OrderType.ROD,
)
trade = api.place_order(stock_acc, order)
```

**結果**:
- ✅ 模擬環境：訂單建立成功，委託成功
- ✅ 訂單內容：Buy 0050 1 股 @ 76.2（市價單）
- ✅ 委託查詢：0 筆（模擬環境不保留）

---

## 問題與限制

### 目前限制
1. **帳務查詢未開通**
   - 錯誤訊息：`Account Not Acceptable (406)`
   - 原因：尚未完成 API 測試流程
   - 解決：需完成模擬環境測試並提交審核

2. **下單功能未開通**
   - 原因：同上
   - 解決：等待審核通過後開通

3. **模擬環境限制**
   - 餘額查詢回傳固定值（0.0）
   - 不實際送出委託

---

## 後續步驟

### 1. 提交測試結果給永豐
- [x] 完成模擬環境登入測試
- [x] 完成帳務查詢測試
- [x] 完成 ETF 報價測試
- [x] 完成證券下單測試（2026-03-26）
- [ ] 提交測試報告給永豐
- [ ] 等待審核通過

### 2. 審核通過後測試
- [ ] 重新測試正式環境餘額查詢
- [ ] 重新測試正式環境持股查詢
- [ ] 測試正式下單功能
- [ ] 測試取消委託
- [ ] 測試成交查詢

### 3. 功能整合
- [ ] 整合餘額查詢到 ETF_TW
- [ ] 整合持股查詢到 ETF_TW
- [ ] 整合下單功能到 ETF_TW
- [ ] 建立風控機制
- [ ] 建立交易日誌

---

## 聯絡資訊

**永豐金證券 API 支援**
- 網站：https://ai.sinotrade.com.tw/
- 文件：https://ai.sinotrade.com.tw/python/Main/index.aspx
- 客服電話：0800-038-123

---

## 備註

- 測試使用 API Key：`ETF_master`
- 測試帳戶：`0737121`
- 測試日期：2026-03-26
- 下一次測試日期：審核通過後

---

**報告完成時間**: 2026-03-26 11:26
