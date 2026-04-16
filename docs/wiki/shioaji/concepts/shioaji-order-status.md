---
title: Shioaji 委託狀態說明 (Order Status)
created: 2026-04-16
updated: 2026-04-16
type: concept
tags: [shioaji.order]
quality: primary
source_type: spec
domain: shioaji
sources: [raw/specs/shioaji-official-docs-2026.md]
---

# Shioaji 委託狀態說明

追蹤委託單的生命週期時，必須理解各個狀態的語義。

| 狀態 (Status) | 語義 | 說明 |
| :--- | :--- | :--- |
| `PendingSubmit` | 傳送中 | 委託已由 SDK 發出，尚未抵達櫃檯。 |
| `PreSubmitted` | 預約單 | 盤前預約單，尚未正式進入交易所。 |
| `Submitted` | 已傳送 | 委託已送達交易所，正在撮合中。 |
| `Filled` | 完全成交 | 委託數量已全數成交。 |
| `PartiallyFilled` | 部分成交 | 僅部分成交，其餘部分仍在撮合或已撤單。 |
| `Cancelled` | 已刪除 | 剩餘未成交的數量已由使用者成功撤銷。 |
| `Failed` | 失敗 | 因風控、餘額不足或價格不合法等原因被拒絕。 |

## 關鍵注意事項
- **真相驗證**：只有狀態為 `Filled` 或 `PartiallyFilled` 時，庫存才會發生變動。
- **落地確認**：建議在接收到 `Submitted` 後，透過 `list_trades` 再次確認委託確實存在於櫃檯。

相關頁面：[[shioaji-unit-safety]]
