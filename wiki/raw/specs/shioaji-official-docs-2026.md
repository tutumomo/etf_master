# Shioaji 官方文件

> 來源：https://sinotrade.github.io/zh/
> 擷取日期：2026-04-16
> 類型：spec / primary

## 網站總覽

Shioaji 是永豐金證券提供的 Python 交易 API，支援台灣證券、期貨、選擇權交易。

- 安裝：`pip install shioaji`（也支援 uv 及 Docker）
- Docker 互動模式：`docker run -it sinotrade/shioaji:latest`
- Docker Jupyter 模式：`docker run -p 8888:8888 sinotrade/shioaji:jupyter`
- 快速安裝：`uv add shioaji --extra speed`

## 登入

### v1.0+（Token 登入）
```python
api = sj.Shioaji()
api.login(api_key="YOUR_API_KEY", secret_key="YOUR_SECRET_KEY")
```

### v1.0 以下（帳號密碼登入）
```python
api.login(person_id="YOUR_PERSON_ID", passwd="YOUR_PASSWORD")
```

### 登入注意
- 若出現 "Sign data is timeout"：電腦時間與伺服器時間差異過大，或需調高 `receive_window`
- `contracts_cb` 參數：商品檔下載完成時觸發 callback
- `subscribe_trade=True`：訂閱所有帳號回報
- `api.subscribe_trade(account)`：訂閱特定帳號回報
- `api.set_default_account(accounts[1])`：設定預設帳號
- `api.logout()`：登出（關閉客戶端及服務端連接）

### 帳號類型
- `StockAccount`（證券帳號）
- `FutureAccount`（期貨帳號）
- 正式 vs 模擬：差異在 `signed` 屬性。`signed=True` 才可正式交易

## 商品檔（Contracts）

### 取得方式
1. 登入時自動下載（`contracts_timeout=10000`），用 `Contracts.status` 確認
2. 登入時 `fetch_contract=False` 禁止自動下載，手動 `api.fetch_contracts(contract_download=True)`

### 查詢
- 證券：`api.Contracts.Stocks['2890']`
- 期貨：`api.Contracts.Futures['TXFA3']`
- 選擇權：`api.Contracts.Options['TXO18000R3']`
- 指數：`api.Contracts.Indexs.TSE['001']`（不可下單，可訂閱行情）

### 證券商品檔欄位
交易所、代碼、符號、名稱、類別、單位、漲停價、跌停價、參考價、更新日期、融資餘額、融券餘額、當沖資訊

### 更新時間
- 07:50 期貨商品檔
- 08:00 全市場商品檔
- 14:45 期貨夜盤
- 17:15 期貨夜盤

## 證券下單

### 委託單參數
| 參數 | 說明 |
|------|------|
| price | 價格（float/int）|
| quantity | 委託數量（int）|
| action | Buy / Sell |
| price_type | LMT（限價）、MKT（市價）、MKP（範圍市價）|
| order_type | ROD / IOC / FOK |
| order_cond | Cash（現股）、MarginTrading（融資）、ShortSelling（融券）|
| order_lot | Common（整股）、Fixing（定盤）、Odd（盤後零股）、IntradayOdd（盤中零股）|
| daytrade_short | 先賣後買（v1.0+，舊版 first_sell）|
| custom_field | 備註（大小寫英文+數字，上限6字）|
| account | 交易帳號 |
| ca | 憑證 |

### 操作
- 下單：`api.place_order(contract, order)`
- 改價：`api.update_order(trade=trade, price=...)`
- 改量：`api.update_order(trade=trade, qty=...)`（只能減少數量）
- 刪單：`api.cancel_order(trade)`
- 狀態更新：`api.update_status(api.stock_account)`

### 委託單狀態
- PendingSubmit：傳送中
- PreSubmitted：預約單
- Submitted：傳送成功
- Failed：失敗
- Cancelled：已刪除
- Filled：完全成交
- PartFilled：部分成交

## 模擬模式

```python
api = sj.Shioaji(simulation=True)
```

模擬環境可用功能：
- 行情：訂閱/退訂、Ticks、Kbars、快照、或有券源、資券餘額、排行
- 下單：委託、更新、取消、查詢狀態、交易紀錄
- 帳務：未實現損益、已實現損益

## 使用限制

### 流量限制（每日）
| 類別 | 30日成交額/口數 | 每日上限 |
|------|----------------|---------|
| 現貨 | 0 元 | 500 MB |
| 現貨 | 1-1 億元 | 2 GB |
| 現貨 | >1 億元 | 10 GB |
| 期貨 | 0 口 | 500 MB |
| 期貨 | 大台1-1000口 / 小台1-4000口 | 2 GB |
| 期貨 | 超過上列口數 | 10 GB |

查詢流量：`api.usage()`

### API 呼叫頻率
| 類別 | 限制 |
|------|------|
| 行情查詢（credit_enquire, short_stock_sources, snapshots, ticks, kbars）| 5秒內上限50次；盤中 ticks 上限10次、kbars 上限270次 |
| 帳務查詢（list_profit_loss_detail, account_balance 等）| 5秒上限25次 |
| 委託操作（place_order, update_status, cancel_order 等）| 10秒上限250次 |

### 連線與訂閱
- 訂閱數量：200 個
- 同一 person_id 最多 5 個連線
- 登入次數：每日上限 1000 次

### 超限處理
- 流量超限：ticks/snapshots/kbars 回傳空值
- 使用量超限：暫停服務 1 分鐘
- 多次超限：暫停 IP 及 ID 使用權限，需聯繫管理員

## 結算（交割款查詢）

```python
api.settlements(api.stock_account)
```

回傳 `SettlementV1` 物件列表，欄位：
- `date`（datetime.date）：交割日期
- `amount`（float）：交割金額
- `T`（int）：Tday（T=0、T=1、T=2）

## 行情功能

- 即時行情-證券：`/tutor/market_data/streaming/stocks/`
- 即時行情-期貨：`/tutor/market_data/streaming/futures/`
- 歷史行情：`/tutor/market_data/historical/`
- 市場快照：`/tutor/market_data/snapshot/`
- 或有券源：`/tutor/market_data/short_stock_source/`
- 資券餘額：`/tutor/market_data/credit_enquires/`
- 排行：`/tutor/market_data/scanners/`
- 處置及注意股：`/tutor/market_data/disposition_attention/`

## 平台特色

- C++ 核心邏輯 + FPGA 訊息交換
- 原生 Python 整合大型 Python 生態系統
- 台灣第一個相容 Linux 的 Python 交易 API
- 支援 AI Coding Agent Skills
- 回呼機制：委託回報、事件回呼
- 非阻塞模式、綁訂報價模式、觸價委託

## 外部連結

- GitHub：https://github.com/Sinotrade/Shioaji
- C# 文件：https://sinotrade.github.io/Shioaji.Csharp/
- Binder 教學：https://mybinder.org/v2/gh/Sinotrade/Sinotrade.github.io/master?filepath=tutorial%2Fshioaji_tutorial.ipynb
- Telegram 群組：https://t.me/joinchat/973EyAQlrfthZTk1