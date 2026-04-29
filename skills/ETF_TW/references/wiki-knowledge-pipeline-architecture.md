---
name: etf-tw-wiki-knowledge-pipeline
description: ETF_TW wiki 知識沉澱 → AI Decision Bridge 上下文注入的完整鏈路。包含 wiki 雙副本路徑、git 追蹤限制、AI 決策只讀哪些 wiki 的硬編碼缺口。
---

# ETF_TW Wiki 知識管理 + AI Decision Pipeline

## 何時使用
- 要把新知識沉澱到 wiki（低估排行、策略、市場觀點等）
- 要驗證 dashboard AI 決策建議是否用到 wiki
- 要修改 AI Decision Bridge 讀取更多 wiki 頁面
- commit wiki 文件到 git 時碰到 gitignore 問題

---

## 核心架構

### Wiki 雙副本路徑

AI Decision Bridge 的 `generate_ai_decision_request.py` 會從兩個 wiki root 讀取：

| Wiki Root | 路徑 | 用途 | Git 追蹤？ |
|-----------|------|------|-----------|
| Profile wiki | `~/.hermes/profiles/etf_master/wiki/` | 含 concepts/ + entities/ 子目錄 | ✅ 追蹤 |
| Instance wiki | `skills/ETF_TW/instances/etf_master/wiki/` | 運行時工作副本 | ❌ 被 `.gitignore` 排除 |

**讀取優先序**：Profile wiki → Instance wiki fallback（`_read_first` 逐路徑找第一個存在且非空的）

### Git 追蹤限制（重要！）

`skills/ETF_TW/.gitignore` 第 25 行排除 `instances/`，所以：
- ❌ `skills/ETF_TW/instances/etf_master/wiki/*.md` **無法 commit**
- ✅ `skills/ETF_TW/wiki/*.md` **可以 commit**

**正確做法**：wiki 檔案寫入 instance wiki（AI pipeline 會讀），同時副本到 `skills/ETF_TW/wiki/`（git 追蹤用）。

---

## AI Decision Bridge 讀取 Wiki 的代碼位置

### 關鍵檔案
`skills/ETF_TW/scripts/generate_ai_decision_request.py`

### 目前硬編碼讀取的 wiki 頁面（L143~150）

```python
market_view_wiki = _read_first([
    d / 'market-view.md' for d in concept_dirs
])
risk_signal_wiki = _read_first([
    d / 'risk-signal.md' for d in concept_dirs
])
```

### wiki_context 輸出結構（L187~195，v1.4.5 更新）

```python
payload['wiki_context'] = {
    "market_view": market_view_wiki,
    "risk_signal": risk_signal_wiki,
    "investment_strategies": investment_strategies_wiki,   # v1.4.5 新增
    "undervalued_ranking": undervalued_ranking_wiki,       # v1.4.5 新增
    "entities": entity_wiki_summaries   # 持倉標的的 entity wiki
}
```

### Wiki 頁面引用狀態（v1.4.5 已修補）

| 頁面 | 存在？ | 被引用？ | wiki_context 鍵 |
|------|--------|----------|-----------------|
| `market-view.md` | ✅ | ✅ | `market_view` |
| `risk-signal.md` | ✅ | ✅ | `risk_signal` |
| `investment-strategies.md` | ✅ | ✅ | `investment_strategies` |
| `undervalued-etf-ranking.md` | ✅ | ✅ | `undervalued_ranking` |

> v1.4.5 修補前，investment-strategies 和 undervalued-ranking 未被引用。現已透過 `generate_ai_decision_request.py` 注入。

---

## 修法：讓 AI 決策引用更多 wiki（v1.4.5 已完成 example）

在 `generate_ai_decision_request.py` 的 `wiki_context` 區塊加入新頁面：

```python
# L143 附近加入
investment_strategies_wiki = _read_first([
    d / 'investment-strategies.md' for d in concept_dirs
])
undervalued_ranking_wiki = _read_first([
    d / 'undervalued-etf-ranking.md' for d in concept_dirs
])

# L187 修改 wiki_context
payload['wiki_context'] = {
    "market_view": market_view_wiki,
    "risk_signal": risk_signal_wiki,
    "entities": entity_wiki_summaries,
    "investment_strategies": investment_strategies_wiki,
    "undervalued_ranking": undervalued_ranking_wiki,
}
```

**v1.4.5 實測驗證**：`generate_ai_decision_request.py` 產出 4 個非空 wiki 欄位：
- `market_view`: 1,917 字元
- `risk_signal`: 2,329 字元
- `investment_strategies`: 5,184 字元
- `undervalued_ranking`: 2,270 字元

未來若需更通用的方案，可改為自動掃描 wiki 目錄下所有 `.md` 檔案注入 context，而非逐一硬編碼。

---

## Wiki 沉澱標準流程

### 1. 寫入 instance wiki（AI pipeline 讀取）
```bash
# 實際工作路徑
~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/wiki/
```

### 2. 副本到 skills/ETF_TW/wiki/（git 追蹤）
```bash
cp skills/ETF_TW/instances/etf_master/wiki/<page>.md skills/ETF_TW/wiki/
```

### 3. 副本到 profile wiki/concepts/（AI pipeline 優先讀取）
```bash
cp skills/ETF_TW/instances/etf_master/wiki/<page>.md ~/.hermes/profiles/etf_master/wiki/concepts/
```

### 4. Git add + commit + push
```bash
git add skills/ETF_TW/wiki/<page>.md
git commit -m "新增 wiki：<頁面標題>"
git push origin main
```

---

## 注意事項

- `concept_dirs` 的搜索路徑是 `[profile_wiki/concepts/, instance_wiki/concepts/, profile_wiki/, instance_wiki/]`
- 如果 wiki 頁面放在 wiki 根目錄（如 `instance_wiki/market-view.md`），第 4 個搜索路徑才會找到它
- 如果同時存在於 profile wiki/concepts/ 和 instance wiki/，`_read_first` 會優先返回 profile wiki 版本
- Entity wiki 只讀取「目前持有」的標的，watchlist 不持有不會讀
- wiki 內容限制：`_load_entity_wiki` 有 `limit=800` 字元截斷；頂層 wiki 頁面無截斷
- **profile wiki/concepts/ 下的版本有 YAML frontmatter**（如 `market-view.md` 的 `--- title: ... ---`），而 `instances/etf_master/wiki/` 下的版本是純 markdown——兩者都會被讀到，`_read_first` 會返回先找到的那個（通常是 profile wiki 版本，含 frontmatter）

## 常見坑

- **Git commit 找不到檔案**：instances/ 被 gitignore 排除 → 用 `git check-ignore -v <path>` 確認 → 需副本到 `skills/ETF_TW/wiki/` 再 commit
- **AI 決策沒引用新 wiki**：代碼只硬編碼了 4 個 wiki 頁面 → 需手動在 `generate_ai_decision_request.py` 加入新頁面的 `_read_first` 和 `wiki_context` 鍵（v1.4.5 已加入 investment-strategies + undervalued-ranking）
- **繁簡體混用**：使用者要求純繁體中文輸出，搜集網路資料後必須確認 wiki 內容無簡體殘留
- **Wiki 內容過大影響 token**：每個 entity 限 800 字元；策略頁面 investment-strategies.md 達 5184 字元會佔用大量 context，需評估 token 預算
- **版本號同步**：修改 wiki pipeline 代碼後，記得同步更新 `SKILL.md version`、`CHANGELOG.md`、git tag