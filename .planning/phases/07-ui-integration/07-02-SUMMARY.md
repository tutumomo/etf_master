---
phase: ui-integration
plan: 02
subsystem: Dashboard
tags: [UI, Trade-Logic, Security]
requirements: [UI-INTEGRATE]
requires: [ui-integration-01]
provides: [Optimized Trade Logic & Positioning UI]
affects: [overview.html]
tech-stack: [Flask, Jinja2]
key-files: [skills/ETF_TW/dashboard/templates/overview.html]
decisions:
  - "將所有交易票據的預設下單量從 1000 股降至 100 股，以符合小額測試習慣"
  - "強制執行儀表板為 'Preview Only'，移除正式下單按鈕以確保交易安全"
  - "根據是否持倉動態顯示或隱藏 '賣出' 按鈕"
metrics:
  duration: 15m
  completed_date: "2026-04-16"
---

# Phase ui-integration Plan 02 Summary: 更新交易票據 UI

## 執行摘要

優化了持倉區塊與關注列表中的交易票據。現在所有票據均預設 100 股，且強制為「預覽模式 (Preview Only)」，移除了直接從 Dashboard 下單的功能，以強化交易安全性。同時實作了動態顯示邏輯：僅對已持倉標的顯示「賣出」選項。

## 關鍵改動

- **預設下單量調整**: 將 `positions` 與 `watchlist` 區塊中的 `qty` input 預設值改為 100。
- **Preview Only 安全限制**:
  - 在所有交易票據標題旁加入 `Preview Only` 標記。
  - 移除 `confirm-box` 與 `submit-btn`。
  - 在預覽結果下方加入提示訊息，告知用戶需使用 CLI 或 Agent 執行正式交易。
- **動態買賣邏輯**:
  - 在 `card_watchlist_intelligence` 區塊中，檢查標的是否已持有。
  - 若未持有，則隱藏「賣出」按鈕，防止無券賣出。
- **Watchlist 交易入口**: 在合併後的關注列表中為每個標的提供完整的交易預覽入口。

## 驗證結果

- [x] 預設交易數量為 100 股。
- [x] 未持倉標的不顯示「賣出」按鈕。
- [x] 成功移除所有票據中的正式下單按鈕。
- [x] 預覽功能仍可正常呼叫後端 Risk Check (pre_flight_gate)。

## Deviations from Plan

- **安全強化**: 除了禁用按鈕外，還移除了確認核取方塊與正式下單按鈕的 UI 元素，並加入明確的導引文字。
