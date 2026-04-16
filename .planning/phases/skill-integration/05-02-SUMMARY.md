---
phase: skill-integration
plan: 05-02
subsystem: ETF_master
tags: [SOUL, stock-analysis, intent-mapping]
requirements: [SKILL-03, SKILL-04]
key_files: [SOUL.md, skills/stock-analysis-tw/scripts/analyze_stock.py]
---

# Phase 5 Plan 05-02: Intent Mapping & State Integration Summary

本計畫成功建立 `ETF_master` 的意圖觸發映射表，並將外部分析技能的結果與核心狀態目錄整合。

## 主要變更

### 1. 技能結果整合 (Task 1)
- 修改 `skills/stock-analysis-tw/scripts/analyze_stock.py`，新增 `--state-dir` 參數。
- 實現分析結果持久化功能，將評分、建議、關鍵訊號與警告存入 `stock_intelligence.json`。
- 測試完成：`0050.TW` 的分析數據已成功寫入 `skills/ETF_TW/instances/etf_master/state/stock_intelligence.json`。

### 2. SOUL.md 意圖映射 (Task 2)
- 在 `SOUL.md` 中新增「意圖觸發映射表 (Intent-Skill Mapping)」。
- 明確定義了不同情境下應調用的技能（`ETF_TW`, `stock-analysis-tw`, `stock-market-pro-tw`, `taiwan-finance`）。
- 建立了「情緒優先」與「數據連動」等核心導引原則。

## 決策與調整
- **數據連動原則**：決定讓所有分析技能在分析完畢後，強制參考 `etf_master` 的 instance 狀態數據，以維持事實真相的一致性。
- **情緒避雷針**：在 SOUL 中明確標註氣憤或焦慮時禁止重度分析，這是基於 Phase 2 交易保險絲邏輯的延伸。

## 驗證結果
- [x] `analyze_stock.py` 可正確生成 `stock_intelligence.json`。
- [x] `SOUL.md` 內容包含完整的映射矩陣。

## 自我檢查
- [x] 腳本變更已 commit (298f5d4)
- [x] SOUL.md 變更已 commit (f8b15c8)
- [x] 檔案路徑與權限符合 Trust Boundary。

## Self-Check: PASSED
