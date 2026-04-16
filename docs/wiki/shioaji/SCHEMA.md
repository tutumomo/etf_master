# Shioaji API Wiki Schema

## Domain
永豐金證券 Shioaji (Python SDK) 官方文件與技術知識庫。

## Conventions
- 檔案命名：小寫、連字號、無空格 (例如 `order-status-codes.md`)
- 頁面必須包含 YAML frontmatter。
- 使用 `[[wikilinks]]` 進行交叉引用 (每頁至少 2 個導外連結)。
- 所有變更必須紀錄於 `log.md`。

## Frontmatter
```yaml
---
title: Page Title
created: 2026-04-16
updated: 2026-04-16
type: entity | concept | comparison | spec
tags: [shioaji.api, shioaji.order, shioaji.market]
quality: primary
source_type: spec
---
```

## Hierarchical Tag Taxonomy
```
shioaji
  shioaji.setup        # 環境安裝、登入、CA 憑證
  shioaji.api          # 核心 API 物件與方法
  shioaji.order        # 委託下單、狀態查詢、改單
  shioaji.market       # 行情訂閱、Snapshot、歷史資料
  shioaji.account      # 帳戶資訊、權益數、持倉
  shioaji.contract     # 合約查詢、商品格式
  shioaji.error        # 錯誤處理、異常代碼
```
