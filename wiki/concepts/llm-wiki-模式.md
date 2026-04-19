---
title: LLM Wiki 模式
created: 2026-04-12
updated: 2026-04-12
type: concept
tags: [知識管理.wiki, 知識管理.方法論, 比較]
sources: [raw/specs/karpathy-llm-wiki-gist-2026.md, raw/articles/aivi-graphify-overview-2026.md]
quality: primary
source_type: spec
---

# LLM Wiki 模式

由 [[andrej-karpathy]] 提出的知識管理模式：讓 LLM 增量建構和維護一個持久化的 wiki，而非每次從頭檢索。創造「持久化、可複利的 artifact」。

## 核心概念

### 分工原則

人類策展輸入並指引分析方向；模型負責：
- 綜合（summarize）
- 交叉引用（cross-reference）
- 一致性維護（maintain consistency）

### 三層架構

| 層級 | 名稱 | 性質 | 誰擁有 |
|------|------|------|--------|
| Layer 1 | Raw Sources | 不可變 | 人類策展 |
| Layer 2 | The Wiki | 可編輯 | LLM 維護 |
| Layer 3 | The Schema | 規則定義 | 人類定義 |

### 三個核心操作

1. **Ingest**：將原始資料整合到 wiki（捕獲 → 警告 → 檢查 → 寫入 → 更新導航）
2. **Query**：利用已編譯的知識回答問題，引用 wiki 頁面
3. **Lint**：一致性檢查（孤立頁面、斷裂連結、過時內容、矛盾）

### 導航機制

- `index.md`：所有頁面的目錄，每頁一行摘要
- `log.md`：時間序列動作日誌，僅追加

## 與 RAG 的對比

| 維度 | RAG | LLM Wiki |
|------|-----|----------|
| 知識取得 | 每次從頭檢索 | 預編譯，持久化 |
| 交叉引用 | 需要額外處理 | 原生 `[雙中括號]` |
| 矛盾處理 | 通常覆蓋 | 標記並並存 |
| 可審核性 | 黑盒 | 可讀的 markdown |
| 維護成本 | 低 | 中（需要 lint） |
| 複利效應 | 無 | 有 |

## 已知風險

- **持久化錯誤**：沒有定期的 lint，錯誤會複利累積（plundrpunk）
- **LLM 上下文品質**：無監督的 LLM 生成內容可能損害 agent 表現（asakin）
- **角色定位**：如果 LLM 是作者，wiki 偏向「個性化研究索引」而非「第二大腦」（gpkc）

## 工程實現

- [[graphify]] — 以知識圖譜形式實現 LLM Wiki 理念，加入 AST 分析和社群偵測
- 本 wiki（llm-wiki skill）— 以 markdown + Obsidian 格式實現

## 相關頁面

- [[andrej-karpathy]] — LLM Wiki 模式的提出者
- [[graphify]] — 圖譜導向的知識管理工具
- [[知識圖譜-vs-RAG]] — 更深入的對比分析
- [[雙通道提取引擎]] — Graphify 的 AST+LLM 雙通道技術