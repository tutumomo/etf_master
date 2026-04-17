# Phase 0 Plan 3 Summary: 修正程式碼路徑混用問題並建立稽核工具 (PATH-03)

**Date:** 2026-04-15
**Goal:** 確認無混用 ~/.openclaw 與 ~/.hermes/profiles/etf_master 路徑的程式碼

## Actions
1. **建立稽核工具:** 建立 `skills/ETF_TW/scripts/audit_paths.sh`，可掃描專案中硬編碼的舊路徑。
2. **修復路徑混用:** 
   - 發現 `skills/ETF_TW/state_legacy_compat_link` 軟連結指向絕對路徑 `~/.openclaw/...`。
   - 已修復為相對路徑 `instances/etf_master/state`。
3. **驗證:** 重新執行稽核工具，結果顯示專案中已無硬編碼的舊路徑。

## Changes
- `skills/ETF_TW/scripts/audit_paths.sh` (New)
- `skills/ETF_TW/state_legacy_compat_link` (Fixed)

## Verification
```bash
bash skills/ETF_TW/scripts/audit_paths.sh
# Result: 0 matches (except in ignored directories)
```

## Commit Hash
- Skills repo: `f2fa71e`
