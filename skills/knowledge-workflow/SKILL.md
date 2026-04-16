---
name: knowledge-workflow
description: "知識工作流編排器 — 根據任務性質自動選擇 graphify（探勘）或 llm-wiki（定居），或串接兩者形成完整的知識生命週期：探勘→沉澱→累積→更新。"
version: 1.0.0
author: ETF_Master
license: MIT
metadata:
  hermes:
    tags: [knowledge, workflow, graphify, llm-wiki, research, orchestration]
    category: research
    related_skills: [graphify, llm-wiki, obsidian, arxiv]
---

# 知識工作流編排器（Knowledge Workflow Orchestrator）

智能選擇與串接 graphify 和 llm-wiki 兩個知識工具，讓 agent 知道何時用哪個、怎麼串、怎麼避免重複做工。

---

## 核心原則：探勘 vs 定居

|| | Graphify（探勘） | LLM Wiki（定居） |
||---|---|---|
|| **比喻** | 地質探勘隊 | 城市建設局 |
|| **做什麼** | 自動發現文件之間的隱藏連結、社群結構 | 把已驗證的知識沉澱成可長期維護的 wiki 頁 |
|| **何時用** | 拿到新材料、新程式碼庫、一次性的分析任務 | 長期經營的領域、需要持續更新的知識庫 |
|| **輸出** | graph.json + HTML 互動圖 + GRAPH_REPORT.md | Markdown 頁面（entities/ concepts/ comparisons/ queries/） |
|| **關聯發現** | 自動（AST + 語義雙軌，有信心分數） | 手工 `[[wikilinks]]` + agent 交叉引用 |
|| **持久性** | 圖譜可增量更新，但偏分析快照 | 持續累積、可 lint、可審核 |
|| **查詢方式** | BFS/DFS 圖遍歷 | search_files + read_file + index.md |

**一句話**：Graphify 發現你不知道的關聯；LLM Wiki 讓你持續累積已知的知識。

---

## 決策樹：何時用哪個？

```
使用者需求
│
├─ 「分析這個程式碼庫/文件夾」 → Graphify 獨立使用
├─ 「找出 X 和 Y 之間的關聯」 → Graphify 獨立使用（query / path）
├─ 「建立/更新我的知識庫」 → LLM Wiki 獨立使用
├─ 「我有新素材，想整理進知識庫」 → 串接流程（先 Graphify 後 Wiki）
├─ 「追蹤某個領域的長期知識」 → LLM Wiki 為主，定期 Graphify 探勘補充
├─ 「比較 A 和 B」 → LLM Wiki（已有頁面）或 Graphify（需要發現新角度）
├─ 「健康檢查我的知識庫」 → LLM Wiki lint
├─ 「視覺化知識結構」 → Graphify（HTML 互動圖）
└─ 「一句話判斷」：
    ├─ 材料是「一堆檔案」→ Graphify 先
    └─ 材料是「一個領域」→ LLM Wiki 先
```

---

## 串接流程：從探勘到定居

### 流程 A：新素材 → 先探勘後定居（最常用）

適用場景：拿到新的一批研究資料、新程式碼庫、新論文集，想同時發現隱藏連結又想長期累積。

**步驟：**

1. **Graphify 探勘**
   ```
   /graphify <素材路徑>
   ```
   - 讓 graphify 自動提取實體、關係、社群結構
   - 產出 `graphify-out/graph.json` 和 `GRAPH_REPORT.md`

2. **閱讀探勘報告，識別有價值的發現**
   ```bash
   read_file graphify-out/GRAPH_REPORT.md
   ```
   - 重點看：社群偵測結果（意想不到的連結）、AMBIGUOUS 邊（需要驗證的推論）、高信心 INFERRED 邊（值得沉澱的發現）

3. **選擇性沉澱到 LLM Wiki**
   - 不是所有圖譜節點都要進 Wiki——只沉澱「已驗證且長期有用」的知識
   - 沉澱判定標準：
     - EXTRACTED 邊（有明確來源）→ 優先沉澱
     - INFERRED 邊（confidence >= 0.8）→ 沉澱但標記為推論
     - AMBIGUOUS 邊 → 不沉澱，待驗證
     - 孤立節點（degree < 2）→ 除非是核心實體，否則不沉澱

4. **寫入 Wiki 頁面**
   - 每個值得沉澱的節點 → 對應一個 concept/ 或 entity/ 頁面
   - 每條值得沉澱的邊 → 對應頁面間的 `[[wikilinks]]`
   - 在頁面的 frontmatter 加上 `graphify_source: true` 標記
   - 更新 `index.md` 和 `log.md`

5. **標記已沉澱**
   ```
   在 log.md 記錄：
   ## [日期] ingest | Graphify → Wiki 遷移
   - 來源：graphify-out/GRAPH_REPORT.md
   - 遷移節點：N 個
   - 遷移邊：M 條
   - 跳過（AMBIGUOUS 或孤立）：K 個
   ```

### 流程 B：Wiki 缺乏連結 → 用 Graphify 補充

適用場景：LLM Wiki 頁面很多但交叉引用不足，想發現頁面之間可能存在的隱藏關聯。

**步驟：**

1. **把 Wiki 當素材餵給 Graphify**
   ```
   /graphify ~/wiki/concepts/ ~/wiki/entities/
   ```
   - 只掃描 Wiki 的二層（不掃 raw/），因為 raw/ 是不可改原始資料

2. **分析圖譜結果**
   - 重點看：graphify 發現了哪些 Wiki 頁面之間的 `semantically_similar_to` 邊
   - 這些是 LLM Wiki 的 wikilinks 遺漏的交叉引用

3. **把有價值的邊補回 Wiki**
   - 每條 `semantically_similar_to` 或 `conceptually_related_to` 邊 → 在對應頁面補上 `[[wikilinks]]`
   - 更新頁面的 `updated` 日期

4. **不需要重複建頁面**——頁面已經存在，只需要補連結

### 流程 C：定期探勘更新

適用場景：Wiki 已穩定運作，但 raw/ 素材逐漸增加，想定期發現新連結。

**步驟：**

1. 對 raw/ 目錄跑 `/graphify <路徑> --update`
2. 比對新發現的邊跟 Wiki 現有頁面
3. 只沉澱「新增的、有價值的」邊到 Wiki
4. 記錄在 log.md

---

## 避免重複做工的規則

1. **已沉澱的知識不重建**：如果 Wiki 已有某實體的頁面，不要因為 Graphify 又偵測到同一實體就建新頁。改為：
   - 檢查 Wiki index.md 是否已有該實體
   - 如有 → 更新現有頁面（補充新資訊、新連結）
   - 如無 → 建新頁面

2. **Graphify 的 INFERRED 邊不直接進 Wiki**：只有經過人工確認或 EXTRACTED 等級的邊才 `[[wikilink]]` 進 Wiki。INFERRED 邊記錄在頁面的「相關推論」段落，標明來源和信心分數。

3. **Wiki 的 `raw/` 不要餵給 Graphify 重複提取**：因為 raw/ 本身就是不可改的原始檔，Graphify 的結果不應改動 raw/。如果需要對 raw/ 做探勘，結果放在 `graphify-out/`，沉澱結論到 Wiki 的 concepts/ 和 entities/。

4. **同一批素材不要同時跑兩個工具**：先 Graphify → 讀報告 → 再沉澱到 Wiki。順序跑，不要平行跑同一批素材。

---

## ETF 投資領域的特殊考量

當這個工作流用於 ETF / 台股投資研究時：

|| 典型任務 | 用哪個 | 說明 ||
|----------|--------|------|
| 分析一份新的 ETF 研究報告 | Graphify 先，找出報告裡的關鍵實體和關聯 |
| 追蹤某個 ETF 的長期知識 | LLM Wiki，持續累積該 ETF 的基本面、技術面、新聞 |
| 比較 0050 vs 00878 | LLM Wiki 的 comparisons/ 頁面 |
| 從一堆券商報告中發現隱藏關聯 | Graphify，用社群偵測找跨報告的連結 |
| 定期更新投資知識庫 | 流程 C，對新增 raw/ 跑 Graphify --update，再沉澱 |
| 檢查知識庫是否過時 | LLM Wiki lint，檢查 stale content |

---

## Pitfalls（踩坑記錄）

### 技能目錄結構與發現機制
- **Hermes 技能掃描器**：user-installed skills 放在 `~/.hermes/skills/` 下，使用 flat 結構（目錄名即技能名），或放在 category 子目錄下（如 `research/`）。兩種結構都會被 `iter_skill_index_files` 遞迴掃描到。
- **YAML frontmatter 格式**：必須有 name、description、version 等欄位，且格式正確才能被技能系統解析。

### Graphify CLI 限制
- **graphify 不能直接對目錄跑探勘**：CLI 只接受 `<command>` 子指令（install, query, benchmark, hook, claude, codex 等），不接受路徑作為參數直接執行探勘。完整的探勘流程需要使用 Agent subagent 逐步執行 skill.md 裡的 Step 1-9 Python 腳本。
- **graphify detect() 只接受單一根目錄**：呼叫 `detect(Path('entities') / Path('concepts'))` 這種多路徑寫法會回傳 0 files。正確做法是傳入包含所有子目錄的根目錄（如 `~/wiki`），讓 detect 遞迴掃描子目錄。
- **graphify 的 Python 模組名是 graphifyy**（pipx 安裝包名帶雙 y），但 CLI 命令是 `graphify`。引用 Python 時需用正確的 venv 路徑：`/Users/tuchengshin/.local/pipx/venvs/graphifyy/bin/python`。
- **graphify 已安裝的圖譜輸出位置**：`~/bio/graphify-out/graph.json` 和 `~/Projects/graphify-out/graph.json` 是現有的圖譜，不要誤刪。
- 此技能引用 `/graphify` 指令，但 graphify 是獨立技能，必須已安裝且可用才能執行串接流程。
- 如果 graphify 未安裝，流程 A/B/C 中的探勘步驟會失敗，需回退到純 LLM Wiki 單獨使用。

### Graphify + Markdown/Wiki 的特殊問題
- **graphify AST extraction 對 .md 檔案回傳 0 nodes**：AST extraction 只能處理程式碼檔（.py, .ts, .go 等）。對於純 markdown 的 wiki，必須自建提取 JSON，然後用 graphify 的 `build_from_json()` 等函數建圖。
- **自建提取方法**：從 wiki 頁面的 `[[wikilinks]]` 和 YAML frontmatter tags 提取實體和關聯，產生 graphify 相容的 extraction JSON 格式：
  ```python
  # 核心提取邏輯：
  # 1. 每個 wiki 頁面 → 一個 node（id=檔名, label=frontmatter.title, type=frontmatter.type, tags=frontmatter.tags）
  # 2. 每條 [[wikilink]] → 一條 EXTRACTED edge（relation="references", confidence_score=1.0）
  # 3. 共享 tags 的頁面對 → INFERRED edges（relation="shares_tag", confidence_score=0.6）
  # 4. 同 type 的頁面對但無共享 tags → 可選 INFERRED edges
  # 5. concept 頁面提到的 entity → EXTRACTED edge（relation="exemplifies", confidence_score=0.9）
  ```
- **提取後建圖流程**：
  ```python
  from graphify.build import build_from_json
  from graphify.cluster import cluster, score_all
  from graphify.export import to_json, to_html
  G = build_from_json(extraction_dict)
  communities = cluster(G)
  cohesion = score_all(G, communities)
  to_json(G, communities, 'output/graph.json')
  to_html(G, communities, 'output/graph.html', community_labels=labels)
  ```
- **Bridge node 分析**（跨社群連接點）：計算每個節點有多少邊連到其他社群，找出同時連接多個社群的「橋樑節點」。這些是隱藏的關聯焦點，例如 00881 雖然名義上是產業型 ETF，但因為科技龍頭選股邏輯橫跨市值型和產業型，成為知識圖譜中的最大橋樑節點。
- **graphify-out/ 不需要放在 wiki 根目錄**：圖譜輸出放在 `~/wiki/graphify-out/` 是可接受的，但 `graphify detect()` 時要注意它也會掃到這些檔案（可加 `.graphifyignore`）。
- **god_nodes() 回傳值型態問題**：`god_nodes()` 在某些 graphify 版本中回傳 dict 作為 node ID（unhashable），導致 `G.nodes[n]` 出錯。改用手動 degree 排序：`sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)`。

### LLM Wiki 實例位置
- **當前活躍的 LLM Wiki**：`~/wiki/`（非 profile 內部路徑，是使用者根目錄下的獨立目錄）
- **已有頁面**：24 頁（15 個 ETF 實體、6 個概念、3 個比較），領域為台灣 ETF 投資
- **SCHEMA.md**：定義了 7 大類型標籤（市值型、高股息、債券型、產業型、跨境型、槓反型、主動型）+ TWSE/TPEX 市場標籤 + 研究標籤 + 家族成員標籤
- **每次 session 開始操作 wiki 前**，必須先讀 SCHEMA.md + index.md + log.md 最近 20 行（這是 llm-wiki skill 的硬規則）

---

## 觸發條件

使用此技能當：
- 使用者提到「知識庫」、「knowledge base」、「wiki」、「知識圖譜」
- 使用者同時需要分析新素材和長期累積知識
- 使用者問「graphify 和 llm-wiki 我該用哪個」
- 使用者有新材料想整理進現有的知識庫
- 使用者想補充 Wiki 頁面之間的交叉引用
- 任何需要知識管理流程決策的場景

---

## 完整串接指令速查

### 一次探勘 + 沉澱（流程 A）
```bash
# Step 1: 探勘
/graphify <素材路徑>

# Step 2: 讀報告（agent 自動）
read_file graphify-out/GRAPH_REPORT.md

# Step 3-4: 沉澱到 Wiki（agent 依據判定標準執行）
# 更新 index.md, 建立新頁面, 更新 log.md
```

### Wiki 連結補強（流程 B）
```bash
# Step 1: 對 Wiki 二層探勘
# 注意：graphify detect() 只接受單一根目錄，不接受多個路徑參數
# 正確做法：傳入 wiki 根目錄，讓 detect 遞迴掃描子目錄
/graphify ~/wiki

# Step 2: 找出 semantically_similar_to 邊
# Step 3: 補上 [[wikilinks]]
```

### 定期更新（流程 C）
```bash
# Step 1: 增量探勘
/graphify ~/wiki/raw/ --update

# Step 2: 比對新發現
# Step 3: 增量沉澱
```