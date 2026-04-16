---
title: Graphify
created: 2026-04-12
updated: 2026-04-14
type: entity
tags: [知識管理.圖譜, AI工具.提取, AI工具.助理, 比較]
sources: [raw/articles/aivi-graphify-overview-2026.md, ETF_TW/graphify-out/GRAPH_REPORT.md]
quality: primary
source_type: article
---

# Graphify

AI coding assistant 的 Skill 插件，核心使命是將任意文件夾中的代碼、文檔、論文、圖片轉化為可查詢的知識圖譜。MIT 開源授權。

## 核心價值

建圖一次後，查詢只消耗原始 token 量的 1/71.5。解決了 LLM 每次都需要重新閱讀整個代碼庫的問題。

## ETF_TW 實測（2026-04-14）

在 ETF_TW 代碼庫（341 檔案，~96,691 字）的實際應用結果：

| 指標 | 數值 |
|------|------|
| 總節點數 | 2,654 |
| 總邊數 | 3,164 |
| 發現社群數 | 528 |
| 代碼/文件/理由節點 | 1224 / 1170 / 260 |
| EXTRACTED 邊 | 75% |
| INFERRED 邊 | 25% |
| 提取方式 | 規則基底（無 LLM token 消耗） |

### 系統架構發現

Graphify 自動發現了 ETF_TW 的核心系統架構：

- **God Nodes**：`Order`（90 邊）、`BaseAdapter`（86 邊）、`Position`（59 邊）
- **跨社群連結**：`Order` 連接 Community 0/1/3；`BaseAdapter` 連接 Community 0/1/10
- **隱藏耦合**：社群偵測發現 `AccountManager` → `BaseAdapter` 的非顯見依賴

### ETF 生態主題群

自動從文件中推斷出 8 個 ETF 生態主題群：
- 00679B（元大美債20年）、00878（國泰永續高股息）出現在多個主題中
- 00929（復華台灣科技優息）、00922（兆豐藍籌30）等為活躍節點

## 雙通道提取引擎

| 通道 | 技術 | 開銷 | 支援範圍 |
|------|------|------|---------|
| Channel A | tree-sitter AST 分析 | 零 LLM 開銷 | 15 種程式語言 |
| Channel B | LLM agent | 需要 token | 文檔、圖片 |

## 三級置信度

| 標籤 | 置信度 | 說明 |
|------|--------|------|
| EXTRACTED | 1.0 | 直接從原始碼提取 |
| INFERRED | 0.6-0.9 | 推斷的關聯 |
| AMBIGUOUS | 低 | 模糊或不可靠 |

## 社群偵測

使用 **Leiden 演算法**發現文件間的隱藏連結和社群結構。ETF_TW 實測發現 528 個社群，其中 10+ 個有明確語義標籤。

## 輸出格式

- HTML（互動圖譜）、JSON（GraphRAG 就緒）、Obsidian Markdown
- 也支援 SVG、GraphML（Gephi/yEd）、Neo4j Cypher

## 管線架構

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

## 在 ETF_TW 中的應用

```bash
# 檢測檔案類型
graphify detect ETF_TW/

# 提取並建圖（規則基底，無 LLM）
python -m graphify extract ETF_TW/ --mode semantic --no-llm

# 查詢圖譜
graphify query "Order 生命週期"
```

## 相關頁面

- [[llm-wiki-模式]] — Graphify 採用的知識管理哲學繼承自 Karpathy 的 LLM Wiki
- [[知識圖譜-vs-RAG]] — 圖譜方法與 RAG 的對比分析（含 ETF_TW 實測數據）
- [[雙通道提取引擎]] — Graphify 的 AST+LLM 雙通道技術詳解
- [[decision-chain]] — Graphify 發現的 ETF_TW 系統決策架構
