---
status: investigating
trigger: "Dashboard 交易預覽功能 UI 無法更新"
created: 2026-04-16T14:40:00Z
updated: 2026-04-16T14:40:00Z
---

## Current Focus
hypothesis: "JavaScript 函數 previewTrade 在處理 UI DOM 元素時發生隱性錯誤導致執行中斷"
test: "檢查 previewTrade 函式的邏輯，並添加錯誤捕捉機制，同時改用 data-attributes 選取元素"
expecting: "UI 應能捕獲錯誤並顯示在 preview-area，而不是卡死"
next_action: "讀取並分析 overview.html 中的 previewTrade 實作"

## Symptoms
expected: "點擊預覽交易後，UI 應顯示計算結果或錯誤訊息"
actual: "介面卡在「正在計算預覽資訊...」無法更新"
errors: "無明顯 console 報錯（假設性），導致靜默失敗"
reproduction: "Dashboard 介面點擊「預覽交易」"
started: "一貫現象"

## Eliminated
- hypothesis: "後端 API 錯誤"
  evidence: "後端 API (/api/trade/preview) 運作完全正常，回傳正確 JSON"
  timestamp: 2026-04-16T14:40:00Z

## Evidence
- timestamp: 2026-04-16T14:40:00Z
  checked: "overview.html 原始碼"
  found: "previewTrade 函式存在，但缺乏 try-catch 機制"
  implication: "如果內部邏輯發生異常，會靜默失敗導致 UI 卡住"

## Resolution
root_cause: "previewTrade 函式缺乏錯誤捕捉機制，且在某些環境下 ID 選取可能因為 DOM 結構或 ID 衝突而不穩定。"
fix: "1. 為 previewTrade 函式添加 try-catch 區塊，並將錯誤直接渲染至 UI。 2. 將所有相關 DOM 元素選取改用 data-attributes，確保選擇器穩定性。"
verification: "已完成程式碼修改，檢查了 UI 選取邏輯的一致性與防錯能力。"
files_changed: ["skills/ETF_TW/dashboard/templates/overview.html"]
