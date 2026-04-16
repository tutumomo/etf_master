---
title: "Shioaji API 使用限制"
created: 2026-04-16
updated: 2026-04-16
type: concept
tags: [制度, Shioaji, API, 限制, 永豐]
domain: tw-finance.trading-api
sources: [raw/specs/shioaji-official-docs-2026.md]
quality: primary
source_type: spec
---

# Shioaji API 使用限制

永豐金 Shioaji API 的流量、頻率、連線與超限處理規則。這些限制影響系統設計——任何自動下單邏輯都必須遵守。

## 流量限制（每日，依近 30 日成交額分級）

| 類別 | 30 日成交額 | 每日上限 |
|------|-----------|---------|
| 現貨 | 0 元 | 500 MB |
| 現貨 | 1–1 億元 | 2 GB |
| 現貨 | >1 億元 | 10 GB |
| 期貨 | 0 口 | 500 MB |
| 期貨 | 大台 1–1000 口 / 小台 1–4000 口 | 2 GB |
| 期貨 | 超過上列口數 | 10 GB |

查詢當前流量：`api.usage()`

## API 呼叫頻率

| 類別 | 功能 | 限制 |
|------|------|------|
| 行情查詢 | credit_enquire, short_stock_sources, snapshots, ticks, kbars | 5 秒內上限 50 次 |
| 行情（盤中） | ticks | 上限 10 次 |
| 行情（盤中） | kbars | 上限 270 次 |
| 帳務查詢 | list_profit_loss_detail, account_balance 等 | 5 秒上限 25 次 |
| 委託操作 | place_order, update_status, cancel_order 等 | 10 秒上限 250 次 |

## 連線與訂閱限制

| 項目 | 限制 |
|------|------|
| 訂閱數量 | 200 個 |
| 同一 person_id 連線數 | 最多 5 個 |
| 登入次數 | 每日上限 1000 次 |

> ⚠️ 呼叫 `api.login()` 即視為建立一條連線。不使用時應 `api.logout()` 釋放連線。

## 超限處理規則

| 情境 | 處理方式 |
|------|----------|
| 流量超限 | ticks / snapshots / kbars 回傳空值，其他功能不受影響 |
| 使用量超限 | 暫停服務 **1 分鐘** |
| 當日連續多次超限 | **暫停 IP 及 ID 使用權限**，需聯繫 Shioaji 管理員處理 |

## 對 ETF_TW 系統的設計影響

1. **行情輪詢間隔**：ticks 每 5 秒最多 10 次 → 設計上至少隔 0.5 秒
2. **帳務查詢節流**：25 次 / 5 秒 → 持倉+餘額查詢不應超過 5 次/秒
3. **委託頻率**：250 次 / 10 秒 → 批量下單需加延遲
4. **連線管理**：程式異常退出未 logout → 佔用連線，5 次即滿 → 需自動 logout 機制
5. **登入重試**：1000 次/日 → 當日重試上限應設在 1000 以內，但實務上 5 連線限制更早觸發

## 關聯

- [[shioaji]] — Shioaji 產品總覽
- [[taiwan-etf-trading]] — 台灣 ETF 交易制度
- [[shioaji-quantity-bug]] — 張股單位 Bug 事故