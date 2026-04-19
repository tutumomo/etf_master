# RELEASE_AUDIT

> 目的：固定記錄 release 的「tag → commit → 變更範圍 → 驗證結果」，確保可追溯。

## 欄位定義
- `Tag`: 發行標籤
- `Tag Commit`: tag 指向的 commit SHA
- `Range`: 與上一個 release 比較的 commit 區間
- `Scope Summary`: 本次變更分類（docs/code/test/wiki）
- `Validation`: 已執行的驗證
- `Operator`: 執行者
- `Time`: 建立時間（Asia/Taipei）

## Records

| Tag | Tag Commit | Range | Scope Summary | Validation | Operator | Time |
|---|---|---|---|---|---|---|
| v1.4.0 | `ea8b0b6ee2a748722b4e7fdb73676c034f15fe9d` | `82680c9..ea8b0b6` | worldmonitor 整合主線（code+docs+tests） | `tests/test_sync_worldmonitor.py`、`pytest tests/ -q`（依 CHANGELOG） | Hermes/Claude-Code | 2026-04-19 |
| v1.4.0-docs-followup | `d7ac4c4b8b2b0008b16c5d96f752e7001e97d3f5` | `ea8b0b6..d7ac4c4` | 實際為混合提交（docs+code+tests+wiki），非純 docs | `git show --stat d7ac4c4` 檢視 22 files changed | Hermes ETF_Master | 2026-04-19 |
| audit-hardening-2026-04-19 | `0e5b11481423087f8d85fddfe4e67db69a5f3fcf` | `d7ac4c4..0e5b114` | branch protection + tag/audit/hook/CI guard | branch protection API 回傳（protected=true）+ remote tag/commit 檢查 | Hermes ETF_Master | 2026-04-19 |

## 使用規範
1. 每次 release / hotfix 推送後，必須新增一列。
2. `Tag Commit` 必須可由 `git show <tag>` 驗證。
3. 若 commit 訊息語意與內容不一致，必須在 `Scope Summary` 明確揭露。
4. 若未完成測試，不可寫「已通過」，請寫「未驗證」。
