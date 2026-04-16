# Live 交易 SOP（標準作業程序）

> 從第一次實際 live 下單經驗萃取，適用於永豐金 Shioaji SDK

---

## Pre-flight 檢查清单

每次正式送單前，必須一次性完成以下檢查：

1. **交易時段確認**
   - 一般盤：09:00–13:30
   - 盤後零股：13:40–14:30
   - 非交易時段 → 直接回覆「非交易時段」，不得送單

2. **環境檢查**
   ```bash
   skills/ETF_TW/.venv/bin/python   # 必須用 project venv
   ```

3. **帳戶狀態**
   - `api.stock_account` 存在且正確
   - 餘額足夠（`api.account_balance()`）
   - 交易額度（`api.trading_limits()`）

4. **商品檔確認**
   - TSE ETF：`api.Contracts.Stocks.TSE.TSE0050`
   - OTC ETF：`api.Contracts.Stocks.OTC.get('00679B')`

5. **CA 憑證**
   - 路徑從 `private/.env` 讀取
   - 密碼 = person_id
   - `api.activate_ca(ca_path, ca_passwd)` 必須成功

---

## 下單流程（盤中零股 — ETF 最常用）

### Step 1：取得 Contract

```python
contract = api.Contracts.Stocks.TSE.TSE00878           # TSE
contract = api.Contracts.Stocks.OTC.get('00679B')       # OTC
```

### Step 2：建立 Order

```python
order = api.Order(
    price=27.25,
    quantity=100,                          # 股，不是張
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.IntradayOdd,
    account=api.stock_account
)
```

### Step 3：送單

```python
trade = api.place_order(contract, order)
```

### Step 4：驗證委託落地（關鍵！）

```python
api.update_status(api.stock_account)
# 確認：status 非 Failed/Inactive
# 確認：ordno 非空
# 確認：broker_order_id 非 null
# broker_order_id 為 null = 幽靈單，禁止輸出「✅ 已正式掛單」
```

### Step 5：查詢成交

```python
api.update_status(api.stock_account)
trades = api.list_trades()
positions = api.list_positions(api.stock_account)
```

---

## 整股差異

```python
quantity=1,                                    # 張（1000股）
order_lot=sj.constant.StockOrderLot.Common,
```

---

## 委託驗證表

| 檢查項目 | 正常 | 異常處理 |
|----------|------|----------|
| status | Submitted/Filled | Failed → 查 cause |
| ordno | 非空 | 空 = 幽靈單 |
| broker_order_id | 非 null | null = 假回單 |

**核心：submit 回應 ≠ 委託落地，必須用 list_trades() 驗證**

---

## 改價/改量/取消

```python
api.update_order(trade=trade, price=new_price)
api.update_order(trade=trade, qty=new_qty)
api.cancel_order(trade)
api.update_status(api.stock_account)  # 每次操作後都要
```

---

## 持倉與餘額對帳

```python
positions = api.list_positions(api.stock_account)
balance = api.account_balance()
pnl = api.list_profit_loss(account, begin_date, end_date)
limits = api.trading_limits(api.stock_account)
```

---

## 錯誤處理

| 錯誤 | 對策 |
|------|------|
| logout segfault (139) | 正常，sys.exit(0) 退出 |
| Contract None | OTC 用 .get()，TSE 用 TSE.TSE0050 |
| CA 失敗 | 確認 .env 路徑+密碼 |
| 非交易時段 | 不送單，直接告知 |
| 餘額不足 | 預算 = price×qty + fee + tax |

---

## Quick Reference

```
Account:    9A9L / 0737121
Venv:       skills/ETF_TW/.venv/bin/python
Env:        private/.env (dotenv)
CA pwd:     person_id
Tickers:    00679B→00679B.TWO, others→.TW
Odd lot:    IntradayOdd=盤中零股(股), Common=整股(張)
```