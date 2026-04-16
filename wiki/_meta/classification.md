# Source Classification Log — 台灣 ETF 投資知識庫

> 記錄攝入時的分類決策。幫助 agent 學習自動分類模式。

## Classification Rules

### URL Patterns
- arxiv.org → paper/primary
- docs.*.io → spec/primary
- medium.com, substack.com → article/secondary
- github.com (README, docs/) → spec/primary
- github.com (issues, discussions) → article/tertiary
- gist.github.com → spec/primary (原始定義/規格) 或 article/secondary (分析)
- news.*.com → news/secondary
- aivi.fyi → article/secondary (第三方產品介紹)
- sinotrade.github.io → spec/primary (官方 API 文件)

### Content Heuristics
- [abstract + methodology + references] → paper/primary
- [code examples + API sections] → spec/primary
- [links to 3+ primary sources] → article/secondary
- [opinion without citations] → article/tertiary

## Classification History
| Date | Source | Assigned Type | Assigned Quality | Reason |
|------|--------|--------------|-----------------|--------|
| 2026-04-11 | etf_universe_tw.json | dataset | primary | 官方市場數據 |
| 2026-04-12 | aivi-graphify-overview-2026.md | article | secondary | 第三方產品介紹頁，aivi.fyi 域名 |
| 2026-04-12 | karpathy-llm-wiki-gist-2026.md | spec | primary | Karpathy 本人的原始概念定義 gist |
| 2026-04-16 | shioaji-official-docs-2026.md | spec | primary | sinotrade.github.io 官方 API 文件，含程式碼範例與端點 |