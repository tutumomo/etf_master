---
title: Shioaji API 核心開發文件 (官方提取版)
created: 2026-04-16
updated: 2026-04-16
type: spec
tags: [shioaji.api, shioaji.order, shioaji.market, shioaji.account]
quality: primary
source_type: spec
domain: shioaji
---

# Shioaji API 核心開發文件

此文件由 https://sinotrade.github.io/zh/ 提取，涵蓋 Shioaji Python SDK 的核心功能。

## 1. 快速開始 (Quick Start)

### 登入與 CA 憑證
```python
import shioaji as sj
api = sj.Shioaji()
api.login(person_id="YOUR_ID", password="YOUR_PASSWORD")
api.activate_ca(ca_path="path/to/cert.pfx", ca_passwd="...", person_id="YOUR_ID")
```

## 2. 委託下單 (Order)

### 股票下單範例
```python
contract = api.Contracts.Stocks["2330"]
order = api.Order(
    price=600, 
    quantity=1, 
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.Common # Common: 張, IntradayOdd: 股
)
trade = api.place_order(contract, order)
```

### 委託狀態 (Status)
- `PendingSubmit`: 傳送中
- `PreSubmitted`: 預約單
- `Submitted`: 已傳送至交易所
- `Filled`: 完全成交
- `PartiallyFilled`: 部分成交
- `Cancelled`: 已刪除
- `Failed`: 失敗

## 3. 帳戶資訊 (Account)

### 持倉查詢
```python
positions = api.list_positions(api.stock_account)
# 注意：quantity 單位為「股」
```

## 4. 市場行情 (Market Data)

### 行情訂閱與快照
```python
@api.on_quote
def quote_callback(exchange, quote):
    print(f"Quote: {quote}")

api.quote.subscribe(api.Contracts.Stocks["2330"], quote_type=sj.constant.QuoteType.Quote)
snapshot = api.snapshots([api.Contracts.Stocks["2330"]])
```

## 5. 重要單位規則 (Safety)
- **整股 (Common)**: 下單量單位為 **「張」**。
- **零股 (IntradayOdd)**: 下單量單位為 **「股」**。
- **庫存 (Positions)**: 回傳量單位皆為 **「股」**。
