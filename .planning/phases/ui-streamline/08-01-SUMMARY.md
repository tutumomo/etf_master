---
phase: 08-ui-streamline
plan: 01
subsystem: Dashboard
tags: [api, pipeline, dashboard]
requires: [UI-STREAMLINE]
provides: [/api/decision/full-pipeline]
affects: [skills/ETF_TW/dashboard/app.py]
tech-stack: [FastAPI, Python, Subprocess]
key-files: [skills/ETF_TW/dashboard/app.py]
decisions:
  - 在 app.py 實作全鏈路同步 helper 並提供 API 端點，支援背景執行與併發鎖定。
metrics:
  duration: 10m
  completed_date: "2026-04-16"
---

# Phase 08 Plan 01: Dashboard 指令集精簡與一鍵同步優化 Summary

## 一句話描述
實作了 `/api/decision/full-pipeline` 端點，整合報價同步、規則掃描與仲裁共識的背景執行管線。

## 主要變更
- **app.py**:
  - 新增 `_run_full_pipeline_helper()`：
    - 依序執行 `refresh_monitoring_state.py`、`run_auto_decision_scan.py` 與 `generate_decision_consensus.py`。
    - 引入 `full_pipeline.lock` 文件鎖機制，防止 10 分鐘內重複觸發併發執行。
    - 執行前刪除 `decision_consensus.json` 以便前端顯示載入中狀態。
    - 使用 `subprocess.Popen` 支援背景非阻塞運行。
  - 新增 `POST /api/decision/full-pipeline`：
    - 提供外部觸發入口，處理鎖定狀態（回傳 429）與錯誤處理。

## 偏離說明
- 無偏離，完全按照計畫執行。
- 額外增加了 `full_pipeline.lock` 以滿足威脅模型中的 DoS 防護要求。

## 驗證結果
- **Helper 驗證**: 通過虛擬環境調用驗證，能正確啟動背景進程並回傳成功狀態。
- **API 驗證**: 通過 `curl` POST 請求驗證，端點能正確響應並啟動管線。

## 待辦項 (Deferred Items)
- 無

## 自我檢查: PASSED
- [x] 所有任務已執行
- [x] API 端點可運作
- [x] 已在子模組 `skills/ETF_TW` 提交變更 (hash: b8de15a)

**Commits:**
- skills/ETF_TW@b8de15a: feat(ui-streamline-01): implement /api/decision/full-pipeline endpoint in app.py
