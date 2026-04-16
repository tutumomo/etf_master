---
phase: ui-integration
plan: 01
subsystem: Dashboard
tags: [UI, Visualization, Performance]
requirements: [UI-INTEGRATE]
requires: []
provides: [Merged Watchlist & Intelligence UI]
affects: [overview.html]
tech-stack: [Flask, Jinja2, LightweightCharts]
key-files: [skills/ETF_TW/dashboard/templates/overview.html]
decisions:
  - "合併 'Tape Context' 與 'Watchlist' 以提升資訊密度"
  - "在 Watchlist 表格中直接顯示技術指標 (RSI, MACD)"
metrics:
  duration: 15m
  completed_date: "2026-04-16"
---

# Phase ui-integration Plan 01 Summary: 合併盤感與關注區塊

## 執行摘要

成功合併了 Dashboard 上的「盤感輔助層」與「關注標的」兩個獨立區塊，現在統一在「關注標的與市場盤感」區塊中呈現。此舉減少了垂直滾動的需要，並讓用戶能一眼看出關注標的的技術面狀態。

## 關鍵改動

- **UI 結構重組**: 移除 `card_tape_context` 與 `card_watchlist`，新增 `card_watchlist_intelligence`。
- **技術指標強化**:
  - 在表格中直接顯示 RSI 與 MACD 數值。
  - 使用 `macd` 與 `macd_signal` 的相對關係決定 MACD 顏色。
- **盤感整合**: 關注列表現在會自動帶入來自 `intraday_tape_context` 的盤感標籤（如：偏多震盪）與相對強弱。
- **操作優化**: 每個關注標的現在都有「交易」、「詳情」與「移除」按鈕。

## 驗證結果

- [x] 成功合併區塊。
- [x] RSI 與 MACD 指標正確顯示。
- [x] 移除按鈕運作正常。
- [x] 詳情圖表展開功能正常。

## Deviations from Plan

None - plan executed exactly as written.
