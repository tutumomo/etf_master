---
phase: "03"
plan: 01
subsystem: Dashboard UI
tags: [UI, Collapsible, Tooltip, Onboarding]
requirements: [TICKET-06, TICKET-07, GIT-01, GIT-02]
status: completed
completed_at: 2026-04-16
---

# Phase 03 Plan 01: Card 摺疊與新手 Tooltip Summary

本階段成功實作了儀表板區塊的可摺疊機制以及新手導引提示，提升了介面的整潔度與易用性。

## 核心變更

### 1. Card 摺疊機制 (TICKET-06)
- **實作方式**：在 `base.html` 中定義了 `.card-collapsible` 相關 CSS 與 JS 函數 `toggleCard`。
- **持久化**：使用 `localStorage` 記錄每個區塊的收合狀態，確保頁面重新整理後狀態不遺失。
- **UI 優化**：所有 Card 區塊皆改為標題可點擊模式，並加上收合指示圖示（▼）。

### 2. 新手 Tooltip / Onboarding Hint (TICKET-07)
- **實作方式**：在 `base.html` 中建立了 CSS-only 的 Tooltip 設施，採用深色金融風格（accent color #7cd6ff）。
- **內容覆蓋**：為「交易模式」、「盤感輔助層」、「決策控制台」與「持倉快照」四個核心區塊增加了易懂的說明文字，幫助無經驗使用者快速上手。

## 修改檔案

- `skills/ETF_TW/dashboard/templates/base.html`: 新增摺疊與提示的 CSS/JS 基礎設施。
- `skills/ETF_TW/dashboard/templates/overview.html`: 更新所有 Card 結構，加入 `toggleCard` 觸發點與 `tooltip` 文字。

## 驗證結果

- **自動化驗證**：`grep` 確認 `toggleCard` 與 `.tooltip` 存在於範本中。
- **人工驗證**：
  - 點擊標題可正常切換 `.collapsed` class 並隱藏內容。
  - 滑鼠移至 `?` 圖示可顯示正確的提示框。
  - 重新整理頁面後，原先收合的區塊維持收合。

## 變更 Commit

- **Sub-repo (skills/ETF_TW)**: `404cbb1` - feat(03-01): implement collapsible cards and onboarding tooltips

## Self-Check: PASSED
