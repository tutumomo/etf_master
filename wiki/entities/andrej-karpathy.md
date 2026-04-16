---
title: Andrej Karpathy
created: 2026-04-12
updated: 2026-04-12
type: entity
tags: [人物.研究者, 知識管理.方法論, 知識管理.wiki]
sources: [raw/specs/karpathy-llm-wiki-gist-2026.md]
quality: primary
source_type: spec
---

# Andrej Karpathy

AI 研究者、OpenAI 共同創辦人、前 Tesla AI 總監。以深度學習教學和 LLM 應用方法論聞名。

## LLM Wiki 模式

Karpathy 在 2026 年提出了 **LLM Wiki 模式**（[原始 Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)），核心概念是讓 LLM 增量建構和維護一個持久化的 wiki，而非每次從頭檢索。

### 核心原則

1. **分工原則**：人類策展輸入並指引分析；模型負責綜合、交叉引用和一致性維護
2. **持久化複利**：知識累積而非每次重建
3. **誠實審計**：每條關係都有置信度標籤，知道什麼是發現的、什麼是推斷的
4. **矛盾標記**：新舊資訊衝突時並存，不覆蓋

### 三層架構

1. **Raw Sources**：不可變的原始資料
2. **The Wiki**：LLM 擁有的 markdown 文件
3. **The Schema**：結構、慣例和標籤分類法定義

## 社群反響

- **AgriciDaniel**：新增 Hot Cache 概念用於 session context
- **Eyaldavid7**：發現 Wiki 在「被刪除/封存邏輯」上顯著優於 RAG
- **plundrpunk**：警告持久化錯誤會複利累積
- **asakin**：引用研究指出無監督的 LLM 生成上下文會損害 agent 表現
- **gpkc**：如果 LLM 是作者，wiki 變成「個性化研究索引」

## 相關頁面

- [[llm-wiki-模式]] — LLM Wiki 模式的完整概念頁
- [[graphify]] — Karpathy 模式的工程實現，Graphify 採用其知識管理哲學
- [[知識圖譜-vs-RAG]] — LLM Wiki 與 RAG 的對比