---
title: 2026-04-29 盤後零股未受理事件
created: 2026-04-29
updated: 2026-04-29
type: incident
tags: [shioaji.order, shioaji.odd_lot, etf_tw.live_submit]
quality: verified
source_type: live_test
domain: shioaji
sources: [concepts/shioaji-unit-safety.md, concepts/shioaji-order-status.md]
---

# 2026-04-29 盤後零股未受理事件

## 摘要

2026-04-29 13:57 左右，ETF_TW 依使用者明確確認，嘗試送出一筆真實測試委託：

- 標的：006208
- 方向：賣出
- 限價：211.50
- 數量：1 股
- 時段：盤後零股時段

系統收到送單回應後，`verify_order_landed` 連續查詢 3 次仍找不到券商委託編號，並將結果記錄為 ghost。使用者也在永豐金證券網站查不到該筆委託，因此判定為「未被券商受理成可查委託」，不是成交延遲。

## 根因

盤後零股時段 13:40-14:30 應使用 `StockOrderLot.Odd`。當時 `sinopac_adapter.py` 對所有 1-999 股零股委託都固定使用 `StockOrderLot.IntradayOdd`，這只適用於一般盤盤中零股。

正確映射：

| 時段 | Shioaji order_lot | quantity 單位 |
|---|---|---|
| 09:00-13:30 | `StockOrderLot.IntradayOdd` | 股 |
| 13:40-14:30 | `StockOrderLot.Odd` | 股 |

## 系統防護結果

- 未驗證落地的委託沒有寫入 `orders_open.json`
- ghost 已寫入 `ghost_orders.jsonl`
- dashboard / cron 不應把這筆視為已落地正式委託
- 使用者端券商網站查無委託，與系統驗證結果一致

## 修正

`sinopac_adapter.py` 與 `sinopac_adapter_enhanced.py` 改為依交易時段選擇零股 order lot：

- `in_after_hours=True`：使用 `StockOrderLot.Odd`
- 其他交易時段：使用 `StockOrderLot.IntradayOdd`

並補上單元測試，鎖住盤中零股與盤後零股兩種分支。

## 後續規則

1. 未取得使用者當次明確確認，不得重送真實委託。
2. 送單回應不等於委託落地；必須以券商查單 / `verify_order_landed` / `orders_open.json` 為準。
3. 盤後零股測試應先確認當下位於 13:40-14:30，且 adapter 使用 `StockOrderLot.Odd`。
4. 若券商網站查無委託，系統也查無 ordno，應視為未受理，不可視為成功下單。

相關頁面：[[shioaji-unit-safety]], [[shioaji-order-status]]
