# Graphify: 將任意文件夾轉化為可查詢知識圖譜

> 來源：https://www.aivi.fyi/llms/graphify
> 分類：article / secondary
> 擷取日期：2026-04-12

---

## 核心定位

Graphify 是一個 AI coding assistant 的 Skill 插件，核心使命是「將任意文件夾中的代碼、文檔、論文、圖片轉化為可查詢的知識圖譜」。它解決了重複閱讀整個代碼庫的問題——建圖一次，查詢只消耗原始 token 的 1/71.5。

MIT 開源授權。

## 雙通道提取引擎

- **Channel A（AST）**：使用 tree-sitter 做 AST 語法分析，零 LLM 開銷，支援 15 種語言
- **Channel B（LLM）**：使用 LLM agent 處理文檔和圖片

## 三級置信度標籤體系

| 標籤 | 置信度 | 說明 |
|------|--------|------|
| EXTRACTED | 1.0 | 直接從原始碼/文件中提取 |
| INFERRED | 0.6-0.9 | LLM 推斷的關聯 |
| AMBIGUOUS | 低 | 模糊或不可靠的連結 |

## 社群偵測

使用 **Leiden 演算法**進行社群偵測，發現文件間的隱藏連結和社群結構。

## 輸出格式

- **HTML**：互動式圖譜視覺化
- **JSON**：GraphRAG 就緒的 graph.json
- **Obsidian**：Markdown vault 格式
- 也支援 SVG、GraphML（Gephi/yEd）、Neo4j Cypher

## 進階功能

- **超邊（Hyperedges）**：超越二元關係的多實體關聯
- **設計決策節點**：記錄「為什麼」而非只是「是什麼」
- **Git Hooks**：自動增量更新
- **檔案監視**：--watch 模式即時同步

## 管線架構

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

模組間透過 Python dictionaries 和 NetworkX graphs 通訊。安全模組處理 URL 驗證和 SSRF 防護。

## 報告特色

- **上帝節點**：識別圖譜中連接度最高的中樞節點
- **驚人連接**：跨模組或跨領域的意外關聯
- **建議問題**：基於圖譜結構自動產生的探索性問題

快取目錄使用 SHA256 實現增量更新。

## OpenClaw 整合

安裝指令：`pip install graphifyy && graphify install --platform claw`

會複製 skill 定義到 `~/.claw/skills/graphify/SKILL.md`。OpenClaw 使用「語義提取使用順序模式而非並行模式」。AST 分析仍為即時。Always-on 模式寫入 `AGENTS.md`。

## 常用指令

```bash
/graphify .                              # 建構圖譜
/graphify query "..."                    # BFS 遍歷查詢
/graphify query "..." --dfs             # DFS 深度查詢
/graphify path "AuthModule" "Database"  # 最短路徑
/graphify add <URL>                      # 新增外部文件
/graphify . --update                     # 增量更新
/graphify . --watch                      # 即時同步
/graphify . --wiki                       # 生成 Wiki
/graphify . --mode deep                  # 深度模式
/graphify hook install                   # 安裝 Git hooks
```

## 使用場景

1. 理解新專案的架構
2. 追蹤依賴關係
3. 解釋核心模組
4. 回答特定問題
5. 新增外部論文
6. 重構後增量更新
7. 透過 Git hooks 自動維護
8. 激進關係發現
9. 生成團隊 Wiki
10. 匯出至 Neo4j 或 Gephi
11. 即時檔案同步
12. 調整社群聚類而無需重新提取