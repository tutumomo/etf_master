---
phase: 03-持倉交易票據UI
plan: 03
subsystem: Dashboard
tags: [API, Flow, Security]
requires: ["03-02"]
provides: [TICKET-03, TICKET-04, TICKET-05]
affects: [app.py, overview.html]
tech-stack: [FastAPI, Python, JS, Subprocess]
key-files: [skills/ETF_TW/dashboard/app.py, skills/ETF_TW/dashboard/templates/overview.html]
decisions:
  - 送單前強制在後端執行 `pre_flight_gate`，且不信任前端的預覽結果。
  - 預覽階段關閉交易時段檢查（允許非交易時段模擬），但正式送單階段強制檢查。
  - 三段式流程（Preview -> Confirm -> Submit）中，Confirm 階段由前端複選框強制介入。
metrics:
  duration: 15m
  completed_date: 2026-04-16
---

# Phase 03 Plan 03: 三段式交易流程與 API Summary

實作了完整的三段式交易流程 (Preview -> Confirm -> Submit)，並在後端整合了 `pre_flight_gate` 風控檢查。使用者現在可以安全地預覽委託影響、確認風險提示後，再正式送出交易指令。

## 關鍵變更

### 1. 後端交易 API (TICKET-03, TICKET-05)
- 在 `app.py` 實作了 `/api/trade/preview`：
  - 串接 `pre_flight_gate` 進行合規檢查。
  - 預估交易總額與手續費環境。
- 在 `app.py` 實作了 `/api/trade/submit`：
  - 二次執行風控檢查（包含強制交易時段檢查）。
  - 使用 `subprocess` 呼叫 `complete_trade.py` 執行實際委託。

### 2. 三段式流轉 UI (TICKET-04)
- 狀態 1 (Input): 使用者輸入參數，點擊「預覽交易」。
- 狀態 2 (Confirm): 若預覽成功且通過風控，顯示交易摘要與「我已確認...」勾選框，並隱藏預覽按鈕。
- 狀態 3 (Submit): 勾選確認後，顯示「正式下單」按鈕。
- 防呆機制：任何參數變更都會重設 UI 狀態回第一階段。

### 3. 風控整合
- 整合了 `sizing_engine_v1`（透過 pre_flight_gate）檢查集中度與單筆上限。
- 實作了買賣單位檢查（張/股區分）。
- 實作了賣出庫存檢查。

## 偏離計畫說明

無 - 三段式流程完全按照計畫實作，並額外優化了輸入變更時的自動重設邏輯。

## 自我檢查: PASSED

- [x] 使用者必須先點擊 Preview，後續才會出現 Confirm 勾選框。
- [x] 使用者勾選 Confirm 後，才會出現 Submit 按鈕。
- [x] 送單請求已通過後端 `pre_flight_gate` 檢查。
- [x] 完成子倉庫 commit 92f6f18。
