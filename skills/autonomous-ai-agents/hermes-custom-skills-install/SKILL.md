---
name: hermes-custom-skills-install
description: >
  安裝自訂技能到 Hermes Agent 的完整流程。
  包含定位技能檔案、放置到正確目錄、驗證結構、理解分類邏輯。
version: v1.0.0
---

# Hermes 自訂技能安裝流程

## 適用情境
- 使用者說「我把技能放到 skills 裡了」但系統沒抓到
- 需要確認技能是否在正確位置
- 需要理解 Hermes 的分類/索引行為

## 步驟

### 1. 定位技能檔案
技能可能在多個位置，按優先順序搜尋：
```bash
# 最可能的位置
ls ~/.hermes/skills/<skill-name>/SKILL.md

# 使用者桌面或專案目錄
ls ~/Desktop/<skill-name>/SKILL.md

# macOS Spotlight 搜尋（最快）
mdfind -name "<skill-name>"
```

### 2. ⚠️ 必須使用 skill_manage 安裝（最關鍵）

**不要手動建目錄寫 SKILL.md！** 即使目錄結構和 YAML 格式完全正確，手動建立的技能可能無法被 skill_view / skills_list 辨識。

正確做法：
```
skill_manage(action='create', name='skill-name', content='--- YAML frontmatter ---\n\n技能內容...')
```

`skill_manage(action='create')` 會：
- 自動安裝到 profile 專用路徑：`~/.hermes/profiles/<profile>/skills/<skill-name>/SKILL.md`
- 正確觸發內部註冊流程
- 立即可被 skill_view / skills_list 辨識

手動放在 `~/.hermes/skills/<skill-name>/SKILL.md` 的技能，雖然檔案系統掃描（rglob）能找到，但 skill_view 會回傳 "Skill not found"。這是因為 runtime 的技能快取在 session 啟動時載入，手動建立的檔案不會自動註冊。

### 3. 驗證技能已正確安裝
```bash
# 用 skill_manage 建立後，立即驗證
skill_view(name='skill-name')  # 應回傳 success: true
skills_list()                    # 應包含新技能
```

如果 skill_view 回傳 "Skill not found"：
1. 確認 SKILL.md 的 YAML frontmatter 格式正確（name, description, version 必填）
2. 確認是用 skill_manage 建立的，不是手動建目錄
3. 最後手段：重新啟動 session

### 4. 分類邏輯（不搬檔案！）
Hermes **只讀取路徑推斷分類，永遠不會搬移檔案**（原始碼無 shutil.move / os.rename）：

| 路徑結構 | parts 長度 | category 結果 |
|----------|-----------|---------------|
| `~/.hermes/skills/ETF_TW/SKILL.md` | 2 | null（無分類） |
| `~/.hermes/skills/finance/ETF_TW/SKILL.md` | 3 | "finance" |

- 放第一層：功能正常，但不會出現在分類篩選中
- 放子資料夾：會被歸類，但需自行建立分類目錄
- skill_manage 建立的技能：category 由 YAML frontmatter 的 `metadata.hermes.category` 決定

## 常見問題

### Q: 技能放好了但 skills_list 沒顯示？
A: **最常見原因：手動建目錄而非用 skill_manage 建立技能。** 解法：刪掉手動建的目錄，改用 `skill_manage(action='create', name='...', content='...')` 重新建立。手動放在 `~/.hermes/skills/` 的技能即使格式正確，也不保證被 runtime 掃描到。

### Q: 放第一層會被系統搬到分類資料夾嗎？
A: 不會。Hermes 只讀不搬。`_get_category_from_path()` 純粹推斷分類名稱。

### Q: 要不要建分類資料夾？
A: 用 skill_manage 建立技能時，分類由 YAML frontmatter 的 `metadata.hermes.category` 決定，不需要手動建子目錄。

### Q: 手動建的技能目錄可以保留嗎？
A: 如果 skill_manage 已成功建立同名技能到 profile 路徑，手動建的副本可以刪除（`rm -rf ~/.hermes/skills/<skill-name>`）。兩份同名技能可能造成混淆。