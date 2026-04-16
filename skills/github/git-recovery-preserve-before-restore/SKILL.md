---
name: git-recovery-preserve-before-restore
description: 在使用者懷疑「昨天好的版本被凌晨壞改動蓋掉」時，先封存現況，再用 git reflog/fsck/dangling commit 搜尋可恢復版本，最後建立獨立 recovery 分支重建功能。
---

# Git Recovery: Preserve Before Restore

## 何時使用
- 使用者說某個「昨天 OK 的版本」不見了
- 懷疑凌晨/後續修改把本地未提交成果蓋掉
- 需要先保住現況，再追查是否存在於 reflog / stash / dangling commit
- 不確定該直接回滾，還是從舊版本重建功能

## 核心原則
1. 先保住，再追查；不要一上來就 hard reset
2. 先建立 rescue branch/tag，避免二次破壞
3. 把「目前乾淨主線」和「要找回的功能版本」分開處理
4. 若找不到功能版本，要明確說「主線保住了，但功能版本沒進 git 歷史」

## 標準流程

### Phase 1：封存現況
在 repo 根目錄：
```bash
git branch rescue/YYYY-MM-DD-before-recovery
git tag rescue-YYYY-MM-DD-before-recovery
```
驗證：
```bash
git show --no-patch --oneline rescue/YYYY-MM-DD-before-recovery
git show --no-patch --oneline rescue-YYYY-MM-DD-before-recovery
```

### Phase 2：查目前工作樹與近期歷史
```bash
git status --short
git log --pretty=format:'%h %ad %s' --date='format:%Y-%m-%d %H:%M:%S %z' -n 12
git reflog --date='format:%Y-%m-%d %H:%M:%S %z' -n 20
```
用途：
- 對齊使用者描述的時間點
- 找 commit / rebase / restore / pull --rebase 痕跡
- 確認是否真的發生過「凌晨後開始出事」

### Phase 3：搜尋可恢復來源
先查 stash：
```bash
git stash list
```
再查 refs：
```bash
git for-each-ref --sort=-committerdate \
  --format='%(refname:short) %(objectname:short) %(committerdate:iso8601) %(subject)' \
  refs/heads refs/tags | head -30
```
最後查 dangling commits：
```bash
git fsck --no-reflogs --full --unreachable --lost-found
```
重點看：
- `unreachable commit <sha>`
- 可能是 rebase 前、本地未掛上的 commit

### Phase 4：檢查可疑 commit 是否真的含遺失功能
```bash
git show --stat --summary --format=fuller <sha>
```
針對關鍵檔案搜字：
```bash
git show <sha>:path/to/file | grep -n 'TradeTicket\|trade-ticket\|CONFIRM_TICKET\|交易'
```
也可直接看關鍵區段：
```bash
git show <sha>:dashboard/templates/overview.html | sed -n '300,430p'
```

### Phase 5：判斷結果
分三種情況：

#### A. 找到完整功能版本
- 建 recovery branch 指向該 commit：
```bash
git checkout -b recover/feature-name <sha>
```
- 在該分支驗證功能，再決定 cherry-pick / merge / patch 回主線

#### B. 主線還在，但功能版本不在 git 歷史
- 明確告知：
  - 目前主線修復仍在
  - 但特定功能版本沒有進 git 歷史，可能是當時未提交本地改動
- 建 recovery branch 從乾淨主線重建：
```bash
git checkout -b recover/feature-name <current-good-sha>
```

#### C. 目前工作樹有凌晨髒改動
如果已確認是錯的、且 HEAD 本身是對的，可先 restore：
```bash
git restore <files>
```
然後再跑 py_compile / smoke test

## ETF_TW 實戰判讀模板
當使用者說：
- 「昨天 18:56 OK」
- 「今天 01:52 後開始出事」
- 「新版 dashboard + 排過雷的 ETF_TW 不見了」

回覆應分清楚：
1. 哪條主線已保住
2. 哪個 UI/功能（如「關注標的可交易」）現在確實缺失
3. 該功能是否存在於 git 歷史
4. 接下來是 recover 還是 rebuild

## 驗證建議
至少做：
```bash
git status --short
python -m py_compile dashboard/app.py
```
若是 web 專案，再做 dashboard restart / HTTP 200 smoke test

## 常見坑
- 只看 `git log` 不看 `reflog`，會漏掉 rebase 前的 commit
- 沒先建 rescue branch/tag 就開始 reset
- 把「主線已保住」和「功能版本存在」混為一談
- 找到 dangling commit 就以為一定含目標功能，必須實際 grep/讀檔驗證
- 使用者在講「版本不見了」時，真正丟的可能是未提交工作樹，不是 commit

## 這次實證
- 先封存：`rescue/2026-04-15-before-recovery` + `rescue-2026-04-15-before-recovery`
- 查到 dangling commit：`deeae64`
- 驗證後發現：它不是「關注標的可交易」版本
- 結論：`b0b10a9` 主線保住，但目標功能未進 git 歷史，需在 recovery branch 重建
