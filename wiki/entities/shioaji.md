---
title: "Shioaji"
created: 2026-04-16
updated: 2026-04-16
type: entity
tags: [AI工具.助理, 發行商-永豐, 交易API]
domain: tw-finance.trading-api
sources: [raw/specs/shioaji-official-docs-2026.md, projects/shioaji-api-rules-p1-2.md, concepts/shioaji-quantity-bug.md]
quality: primary
source_type: spec
---

# Shioaji

永豐金證券的 Python 交易 API——台灣第一個跨平台（含 Linux）Python 交易介面，以 C++ 為核心、FPGA 處理訊息交換。

## 基本資料

| 項目 | 內容 |
|------|------|
| **開發商** | 永豐金證券（Sinotrade）|
| **語言** | Python（原生整合 NumPy/pandas/PyTorch/TensorFlow）|
| **底層** | C++ 核心邏輯 + FPGA 訊息交換 |
| **安裝** | `pip install shioaji` |
| **GitHub** | https://github.com/Sinotrade/Shioaji |
| **官方文件** | https://sinotrade.github.io/zh/ |
| **C# 版本** | https://sinotrade.github.io/Shioaji.Csharp/ |
| **Telegram 群組** | https://t.me/joinchat/973EyAQlrfthZTk1 |

## 登入方式

| 版本 | 認證方式 | 參數 |
|------|----------|------|
| v1.0+ | Token | `api_key` + `secret_key` |
| v1.0- | 帳號密碼 | `person_id` + `passwd` |

帳號分 `StockAccount`（證券）及 `FutureAccount`（期貨）。`signed=True` 才可正式交易。

### 模擬模式
```python
api = sj.Shioaji(simulation=True)
```
- 行情功能：訂閱/Ticks/Kbars/快照/或有券源/資券餘額/排行
- 下單功能：委託/更新/取消/查詢
- 帳務：僅未實現損益+已實現損益

## 商品檔（Contracts）

| 類別 | 查詢語法 | 可下單 |
|------|----------|--------|
| 證券 | `api.Contracts.Stocks['2890']` | ✅ |
| 期貨 | `api.Contracts.Futures['TXFA3']` | ✅ |
| 選擇權 | `api.Contracts.Options['TXO18000R3']` | ✅ |
| 指數 | `api.Contracts.Indexs.TSE['001']` | ❌（僅行情）|

**證券欄位**：交易所、代碼、符號、名稱、類別、單位、漲停價、跌停價、參考價、更新日期、融資餘額、融券餘額、當沖資訊

**更新時間**：07:50（期貨）→ 08:00（全市場）→ 14:45（夜盤）→ 17:15（夜盤）

## 證券下單

| 參數 | 說明 |
|------|------|
| `price_type` | LMT（限價）/ MKT（市價）/ MKP（範圍市價）|
| `order_type` | ROD / IOC / FOK |
| `order_cond` | Cash（現股）/ MarginTrading（融資）/ ShortSelling（融券）|
| `order_lot` | Common（整股）/ Fixing（定盤）/ Odd（盤後零股）/ IntradayOdd（盤中零股）|

### 操作 API
- 下單：`api.place_order(contract, order)`
- 改價：`api.update_order(trade, price=...)`
- 改量：`api.update_order(trade, qty=...)`（**只能減少**）
- 刪單：`api.cancel_order(trade)`
- 狀態同步：`api.update_status(api.stock_account)`

### 委託狀態
PendingSubmit → PreSubmitted → Submitted → Filled / PartFilled / Cancelled / Failed

## 使用限制

> 完整限制詳見 [[shioaji-api-limits]]

- 流量：依 30 日成交額分級（500MB / 2GB / 10GB）
- 頻率：行情 5s/50次、帳務 5s/25次、委託 10s/250次
- 連線：同一 person_id 最多 5 連線，訂閱 200 個，登入 1000次/日
- 超限：暫停 1 分鐘；多次超限暫停 IP+ID

## 結算

> 詳見 [[settlement-t2]]（含 API 欄位說明）

`api.settlements(api.stock_account)` 回傳 T=0/1/2 交割時程與金額。

## 已知行為陷阱

> ⚠️ 以下來自實戰踩坑經驗，與官方文件互補

1. **張股單位地雷**：`quantity < 1000` 時 API 不拒絕，靜默升級為 1 張（详见 [[shioaji-quantity-bug]]）
2. **`list_trades()` 不可靠**：已成交單幾乎回傳空陣列，Fill 監控應改用 `list_orders()` 輪詢
3. **帳面餘額 ≠ 可用現金**：含券商墊付，T+2 前不是真實可用金額（详见 [[settlement-t2]]）
4. **`account_balance()` 信用額度**：顯示 500,000 是信用額度，非真實現金

详尽行為規則 → [[shioaji-api-rules-p1-2]]

## 關聯

- [[006204-sinopac-weighted]] — 永豐發行的市值型 ETF
- [[taiwan-etf-trading]] — 台灣 ETF 交易制度總覽
- [[settlement-t2]] — T+2 交割機制
- [[shioaji-quantity-bug]] — 張股單位 Bug 事故報告
- [[etf-發行商生態]] — 台灣 ETF 發行商版圖