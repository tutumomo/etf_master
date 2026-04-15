---
phase: 03-持倉交易票據UI
plan: 02
subsystem: Dashboard
tags: [UI, Ticketing, Trades]
requires: []
provides: [TICKET-01, TICKET-02]
affects: [overview.html]
tech-stack: [Flask, Jinja2, JS]
key-files: [skills/ETF_TW/dashboard/templates/overview.html]
decisions:
  - 在每一行持倉下方實作展開式交易票據，並支援多個票據同時展開。
  - 買賣方向採用 Radio + 樣式控制的方式實作自訂 Segmented Control。
metrics:
  duration: 10m
  completed_date: 2026-04-16
---

# Phase 03 Plan 02: 持倉交易入口與展開票據 UI Summary

實作了持倉表格的「交易」按鈕入口，以及對應的隱藏式交易票據區塊。使用者現在可以點擊交易按鈕展開一個 inline 的票據表單，包含買賣方向、數量、價格輸入，並可進行交易預覽。

## 關鍵變更

### 1. 持倉表格更新 (TICKET-01)
- 在 `overview.html` 的持倉快照表格中新增了「操作」欄位。
- 加入了 `toggleTradeTicket(symbol)` 呼叫的「交易」按鈕，主列保持整潔，不直接顯示輸入框。

### 2. 內嵌交易票據實作 (TICKET-02)
- 在每行持倉下方新增了 `id="ticket-{{ symbol }}"` 的隱藏列。
- 票據內包含：
  - 買賣方向切換（買進綠色、賣出紅色）。
  - 數量輸入（預設 1000 股，即 1 張）。
  - 價格輸入（預設帶入持倉現價）。
  - 預覽交易與取消按鈕。

### 3. 前端交互邏輯
- 實作了 `toggleTradeTicket` 控制區塊展開。
- 實作了 `selectSide` 處理買賣按鈕樣式切換與 radio 選項連動。
- 實作了 `previewTrade` 預覽區域切換邏輯（API 對接將於下一個計畫完成）。

## 偏離計畫說明

無 - 計畫執行與預期一致。

## 已知 Stubs

- `previewTrade` 與 `executeTrade` 目前呼叫的 `/api/trade/preview` 與 `/api/trade/submit` 尚未在後端實作，將於 Plan 03 完成。

## 自我檢查: PASSED

- [x] 持倉表格具備交易入口按鈕。
- [x] 點擊交易按鈕能展開/收合專屬的交易票據區塊。
- [x] 票據內具備完整的基礎交易參數輸入欄位。
- [x] 完成子倉庫 commit 0ff8327。
