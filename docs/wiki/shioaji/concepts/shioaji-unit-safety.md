---
title: Shioaji 交易單位安全規則 (Unit Safety)
created: 2026-04-16
updated: 2026-04-16
type: concept
tags: [shioaji.order, shioaji.account]
quality: primary
source_type: spec
domain: shioaji
sources: [raw/specs/shioaji-official-docs-2026.md]
---

# Shioaji 交易單位安全規則

在 Shioaji API 中，單位誤用是造成交易錯誤的主要原因。必須嚴格區分「張 (Lot)」與「股 (Share)」。

## 1. 下單單位 (Quantity)
下單時 `quantity` 的含義取決於 `order_lot` 的設定：

- **整股下單 (`StockOrderLot.Common`)**: 
  - `quantity` 的單位是 **「張」**。
  - 1 張 = 1000 股。
- **零股下單 (`StockOrderLot.IntradayOdd` / `StockOrderLot.Odd`)**:
  - `quantity` 的單位是 **「股」**。

### 安全警告 ⚠️
**錯誤範例**：若想買 100 股，卻設定為 `Common` 並給予 `quantity=100`，則會誤下單買入 **100 張 (即 100,000 股)**。

## 2. 庫存單位 (Positions)
- 透過 `api.list_positions()` 查詢回傳的 `quantity` 單位一律為 **「股」**。
- 不論該庫存是透過整股還是零股買入，查詢結果皆以「股」呈現。

## 3. 實作建議
在系統中建議建立統一的轉換函數：
```python
def normalize_to_shares(qty, lot_type):
    if lot_type == "Common":
        return qty * 1000
    return qty
```

相關頁面：[[shioaji-order-flow]]
