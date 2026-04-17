---
phase: "08"
plan: 02
subsystem: Dashboard
tags: [ui, streamline, dashboard]
requires: [UI-STREAMLINE]
provides: [runFullPipelineSync]
affects: [skills/ETF_TW/dashboard/templates/overview.html]
tech-stack: [HTML, JavaScript, CSS]
key-files: [skills/ETF_TW/dashboard/templates/overview.html]
decisions:
  - 將多個分散的同步、掃描、AI 生成按鈕合併為一個「一鍵同步與全量分析」按鈕，置於 Trading Mode 區塊。
  - 移除 redundant 的手動觸發 JS 函數，清理程式碼。
metrics:
  duration: 15m
  completed_date: "2026-04-16"
---

# Phase 08 Plan 02: Dashboard 指令集精簡與一鍵同步優化 Summary

## 一句話描述
重構了 Dashboard 介面，將分散的手動按鈕合併為「一鍵同步與全量分析 (Full Sync)」，顯著提升了操作效率。

## 主要變更
- **overview.html**:
  - 新增醒目的「一鍵同步與全量分析 (Full Sync)」按鈕，並具備執行時的 Loading 狀態與 Banner 提示。
  - 實作 `runFullPipelineSync()` JS 函數，調用 `/api/decision/full-pipeline`。
  - 移除以下冗餘按鈕：
    - 「立即同步資料」、「立即更新 🔄」、「立即規則掃描」。
    - AI Bridge 面板的「刷新背景資訊」、「生成 AI 建議」、「全部重跑」。
  - 移除對應的 JS 處理函數，使前端腳本更加收斂。

## 偏離說明
- 無偏離，完全按照計畫執行。
- ⚡ 由於 `AUTO_CFG=true`，已自動核准 `checkpoint:human-verify` 任務。

## 驗證結果
- **UI 驗證**: 確認 `runFullPipelineSync` 已正確實作並綁定至新按鈕。
- **Redundancy 驗證**: 成功移除 6 個冗餘按鈕及其背後的 JS 函數。

## 待辦項 (Deferred Items)
- 無

## 自我檢查: PASSED
- [x] 所有任務已執行
- [x] UI 精簡目標達成
- [x] 已在子模組 `skills/ETF_TW` 提交變更 (hash: 84520c9)

**Commits:**
- skills/ETF_TW@84520c9: feat(ui-streamline-02): refactor overview.html to merge sync buttons
