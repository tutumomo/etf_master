# Shioaji API 參考手冊 (永豐金證券 Python SDK)

> 基於 sinotrade.github.io 官方文件整理，版本 v1.3.2+
> 最後更新：2026-04-13

---

## 目錄

1. [登入 (Login)](#1-登入)
2. [商品檔 (Contracts)](#2-商品檔)
3. [股票下單 (Stock Order)](#3-股票下單)
4. [盤中零股 (Intraday Odd)](#4-盤中零股)
5. [委託更新/取消 (Update/Cancel)](#5-委託更新取消)
6. [委託狀態 (Order Status)](#6-委託狀態)
7. [持倉查詢 (Positions)](#7-持倉查詢)
8. [帳戶餘額 (Balance)](#8-帳戶餘額)
9. [損益查詢 (Profit/Loss)](#9-損益查詢)
10. [保證金 (Margin)](#10-保證金)
11. [交割款 (Settlements)](#11-交割款)
12. [交易額度 (Trading Limits)](#12-交易額度)
13. [回呼事件 (Callbacks)](#13-回呼事件)
14. [漲跌停計算 (Limit Up/Down)](#14-漲跌停計算)
15. [快照 (Snapshots)](#15-快照)
16. [串流行情 (Streaming)](#16-串流行情)
17. [歷史資料 (Historical)](#17-歷史資料)
18. [非阻塞模式 (Non-Blocking)](#18-非阻塞模式)
19. [模擬環境 (Simulation)](#19-模擬環境)
20. [快速入門 (Quickstart)](#20-快速入門)
21. [ETF 專用筆記](#21-etf-專用筆記)
22. [已知問題](#22-已知問題)

---

## 1. 登入

### API Key 登入（推薦）

```python
import shioaji as sj
api = sj.Shioaji()
api.login(
    api_key="YOUR_API_KEY",
    secret_key="YOUR_SECRET_KEY"
)
```

### 帳號密碼登入

```python
api = sj.Shioaji()
api.login(
    person_id="YOUR_PERSON_ID",
    passwd="YOUR_PASSWORD",
)
```

### 登入參數

| 參數 | 類型 | 說明 |
|------|------|------|
| api_key | str | API 金鑰 |
| secret_key | str | 密鑰 |
| person_id | str | 身分證字號 |
| passwd | str | 密碼 |
| fetch_contract | bool | 是否從快取讀取商品檔 (預設 True) |
| contracts_timeout | int | 取得商品檔 timeout (預設 0 ms) |
| contracts_cb | Callable | 取得商品檔 callback |
| subscribe_trade | bool | 是否訂閱委託/成交回報 (預設 True) |
| receive_window | int | 登入有效執行時間 (預設 30000 ms) |

### 商品檔回呼

```python
api.login(
    api_key="KEY", secret_key="SECRET",
    contracts_cb=lambda security_type: print(f"{repr(security_type)} fetch done.")
)
# 依序: Index, Future, Option, Stock
```

### 列出帳號

```python
accounts = api.list_accounts()
# [StockAccount(...), FutureAccount(...)]

# 預設股票帳號
api.stock_account
# 預設期貨帳號
api.futopt_account

# 切換預設帳號
api.set_default_account(accounts[1])
```

### 訂閱/取消委託回報

```python
api.subscribe_trade(account)
api.unsubscribe_trade(account)
```

### 登出

```python
api.logout()  # → True (注意：會觸發 segfault exit 139，見已知問題)
```

---

## 2. 商品檔

### 延遲載入商品檔

```python
# 不在登入時自動載入
api.login(api_key="KEY", secret_key="SECRET", fetch_contract=False)
api.fetch_contracts(contract_download=True)
```

### 設定 timeout

```python
api.login(api_key="KEY", secret_key="SECRET", contracts_timeout=10000)
```

### 查詢股票

```python
# 方式一：代碼直接查
api.Contracts.Stocks["2890"]

# 方式二：交易所+代碼
api.Contracts.Stocks.TSE.TSE2890

# OTC 查詢（ETF 常用！例如 00679B）
api.Contracts.Stocks.OTC.get('00679B')
```

### Stock 物件欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| exchange | Exchange | 交易所 {OES, OTC, TSE} |
| code | str | 商品代碼 |
| symbol | str | 符號 |
| name | str | 商品名稱 |
| category | str | 類別 |
| unit | int | 單位（整股=1000, 零股=1） |
| limit_up | float | 漲停價 |
| limit_down | float | 跌停價 |
| reference | float | 參考價 |
| update_date | str | 更新日期 |
| day_trade | DayTrade | 可否當沖 {Yes, No, OnlyBuy} |

### 查詢期貨/選擇權

```python
api.Contracts.Futures["TXFA3"]
api.Contracts.Futures.TXF.TXF202301

api.Contracts.Options["TXO18000R3"]
api.Contracts.Options.TXO.TXO20230618000P
```

### 查詢指數

```python
api.Contracts.Indexs.TSE["001"]
# Index(exchange=TSE, code='001', symbol='TSE001', name='加權指數')
```

---

## 3. 股票下單

### Order 參數

| 參數 | 類型 | 說明 |
|------|------|------|
| price | float/int | 價格 |
| quantity | int | 委託數量 |
| action | Action | {Buy, Sell} |
| price_type | StockPriceType | {LMT:限價, MKT:市價, MKP:範圍市價} |
| order_type | OrderType | {ROD, IOC, FOK} |
| order_cond | StockOrderCond | {Cash:現股, MarginTrading:融資, ShortSelling:融券} |
| order_lot | StockOrderLot | {Common:整股, Fixing:定盤, Odd:盤後零股, IntradayOdd:盤中零股} |
| daytrade_short | bool | 先賣後買 |
| custom_field | str | 備註（英文+數字，最長6字） |
| account | Account | 下單帳號 |
| ca | binary | 憑證 |

### 整股買入範例

```python
contract = api.Contracts.Stocks.TSE.TSE2890

order = api.Order(
    price=17,
    quantity=3,
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.Common,
    custom_field="test",
    account=api.stock_account
)

trade = api.place_order(contract, order)
```

### place_order 簽名

```python
api.place_order(
    contract: shioaji.contracts.Contract,
    order: shioaji.order.Order,
    timeout: int = 5000,
    cb: Callable = None,
) -> shioaji.order.Trade
```

### Trade 回傳物件

```python
Trade(
    contract=Stock(...),
    order=Order(
        action='Buy', price=17, quantity=3,
        id='531e27af',       # ← trade id
        seqno='000002',      # ← 平台單號
        ordno='000001',      # ← 委託書號
        account=Account(...),
        ...
    ),
    status=OrderStatus(
        id='531e27af',
        status='PendingSubmit',  # ← 狀態
        status_code='00',
        order_datetime=datetime(...),
        deals=[]
    )
)
```

### 常見下單組合

```python
# 現股買進
action=sj.constant.Action.Buy
order_lot=sj.constant.StockOrderLot.Common

# 現股賣出
action=sj.constant.Action.Sell
order_lot=sj.constant.StockOrderLot.Common

# 當沖先賣
action=sj.constant.Action.Sell
daytrade_short=True
```

---

## 4. 盤中零股

> ETF 零股下單的關鍵設定！

### 範例

```python
contract = api.Contracts.Stocks.TSE.TSE0050

order = api.Order(
    price=90,
    quantity=10,        # 單位是「股」，不是張
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.IntradayOdd,  # ← 關鍵
    account=api.stock_account,
)

trade = api.place_order(contract, order)
```

### IntradayOdd vs Odd

| 類型 | 常數 | 說明 | 時段 |
|------|------|------|------|
| Common | StockOrderLot.Common | 整股 | 09:00-13:30 |
| IntradayOdd | StockOrderLot.IntradayOdd | 盤中零股 | 09:00-13:30 |
| Odd | StockOrderLot.Odd | 盤後零股 | 13:40-14:30 |

### 重點

- IntradayOdd 數量單位是**股**（不是張），100股=1張的零股
- 盤中零股可跟整股同時段交易
- 盤後零股只能 13:40-14:30
- ETF 常用 IntradayOdd 買小額（如 100 股）

---

## 5. 委託更新/取消

### 更新狀態

```python
api.update_status(api.stock_account)
trades = api.list_trades()
```

### update_status 簽名

```python
api.update_status(
    account: Account = None,
    trade: Trade = None,
    timeout: int = 5000,
    cb: Callable = None,
)
```

### 改價

```python
api.update_order(trade=trade, price=17.5)
api.update_status(api.stock_account)
# trade.status.modified_price → 17.5
```

### 改量

```python
api.update_order(trade=trade, qty=1)
api.update_status(api.stock_account)
# trade.status.cancel_quantity → 被取消的數量
```

### update_order 簽名

```python
api.update_order(
    trade: Trade,
    price: Union[int, float] = None,
    qty: int = None,
    timeout: int = 5000,
    cb: Callable = None,
) -> Trade
```

### 取消委託

```python
api.cancel_order(trade)
api.update_status(api.stock_account)
# trade.status.status → 'Cancelled'
# trade.status.cancel_quantity → 原委託數量
```

---

## 6. 委託狀態

### OrderStatus 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | str | trade id |
| status | Status | 狀態列舉 |
| status_code | str | '00' = 正常 |
| order_datetime | datetime | 委託時間 |
| order_quantity | int | 委託數量 |
| cancel_quantity | int | 取消數量 |
| modified_price | float | 改價後價格 |
| deals | list[Deal] | 成交明細 |

### Status 列舉

| 狀態 | 說明 |
|------|------|
| PendingSubmit | 待送出 |
| PreSubmitted | 預約中 |
| Submitted | 已送出 |
| Cancelled | 已取消 |
| Filled | 已成交 |
| Failed | 失敗 |
| Inactive | 未激活 |

### Deal 物件

```python
Deal(seq='000001', price=17, quantity=3, ts=1673501631.62918)
```

---

## 7. 持倉查詢

### 列出持倉

```python
api.list_positions(api.stock_account)

# 回傳:
# [
#   PositionV1(code='2890', direction='Buy', quantity=1, price=10.1, pnl=100.0, ...),
#   ...
# ]
```

### list_positions 簽名

```python
api.list_positions(
    account: Account = None,
    unit: Unit = Common,
    timeout: int = 5000,
    cb: Callable = None,
) -> List[PositionV1]
```

### PositionV1 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| code | str | 商品代碼 |
| direction | Action | 買賣別 |
| quantity | int | 數量 |
| price | float | 成本價 |
| pnl | float | 未實現損益 |
| yd_quantity | int | 昨日數量 |
| margin | int | 保證金 |

---

## 8. 帳戶餘額

### 查詢餘額

```python
api.account_balance()
api.account_balance(account=api.stock_account)

# AccountBalance(
#   status=Fetched,
#   acc_balance=100000.0,
#   date='2023-01-06 13:30:00',
#   errmsg=''
# )
```

### account_balance 簽名

```python
api.account_balance(
    account: Account = None,
    timeout: int = 5000,
    cb: Callable = None,
) -> AccountBalance
```

### 回傳欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| status | FetchStatus | 資料回傳狀態 |
| acc_balance | float | 餘額 |
| date | str | 查詢日期 |
| errmsg | str | 錯誤訊息 |

---

## 9. 損益查詢

### 查詢損益

```python
profitloss = api.list_profit_loss(
    api.stock_account,
    '2020-05-05',
    '2020-05-30'
)
```

### list_profit_loss 簽名

```python
api.list_profit_loss(
    account: Account = None,
    begin_date: str = '',
    end_date: str = '',
    unit: Unit = Common,
    timeout: int = 5000,
    cb: Callable = None,
) -> List[StockProfitLoss]
```

### StockProfitLoss 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | int | 明細查詢 ID |
| code | str | 商品代碼 |
| seqno | str | 平台單號 |
| dseq | str | 委託書號 |
| quantity | int | 數量 |
| price | float | 價格 |
| pnl | float | 損益 |
| pr_ratio | float | 損益比 |
| cond | StockOrderCond | 交易條件 |
| date | str | 交易日期 |

### 損益明細

```python
detail = api.list_profit_loss_detail(
    api.stock_account,
    detail_id=0
)
```

### 損益彙總

```python
summary = api.list_profit_loss_summary(
    api.stock_account,
    '2020-05-05',
    '2020-05-30'
)
# summary.profitloss_summary → 逐筆
# summary.total → ProfitLossTotal(quantity, buy_cost, sell_cost, pnl, pr_ratio)
```

---

## 10. 保證金

> 期貨帳號專用，ETF 不使用

```python
api.margin(api.futopt_account)
# Margin(yesterday_balance=6000.0, today_balance=6000.0,
#         deposit_withdrawal=0.0, fee=0.0, tax=0.0,
#         initial_margin=0.0, maintenance_margin=0.0, ...)
```

---

## 11. 交割款

```python
settlements = api.settlements(api.stock_account)

# [
#   SettlementV1(date=2022-10-13, amount=0.0, T=0),
#   SettlementV1(date=2022-10-14, amount=0.0, T=1),
#   ...
# ]
```

### settlements 簽名

```python
api.settlements(
    account: Account = None,
    timeout: int = 5000,
    cb: Callable = None,
) -> List[SettlementV1]
```

---

## 12. 交易額度

```python
api.trading_limits(api.stock_account)

# TradingLimits(
#   status=Fetched,
#   trading_limit=1000000,
#   trading_used=0,
#   trading_available=1000000,
#   margin_limit=0,
#   margin_used=0,
#   ...
# )
```

---

## 13. 回呼事件

### 事件回呼（連線/訂閱狀態）

```python
@api.quote.on_event
def event_callback(resp_code: int, event_code: int, info: str, event: str):
    print(f'Event code: {event_code} | Event: {event}')

# Event code: 16 | Event: Subscribe or Unsubscribe ok
```

### 委託/成交回呼

```python
def order_cb(stat, msg):
    print('my_order_callback')
    print(stat, msg)

api.set_order_callback(order_cb)
```

### OrderState.StockOrder 回呼格式

```python
{
    'operation': {
        'op_type': 'New',          # New/Cancel/UpdatePrice/UpdateQty
        'op_code': '00',           # 00=成功
        'op_msg': ''
    },
    'order': {
        'id': '97b63e2f',          # trade id
        'seqno': '267677',
        'ordno': 'IM394',          # 委託書號
        'action': 'Buy',
        'price': 16.0,
        'quantity': 1,
        'order_lot': 'Common',
        ...
    },
    'status': {
        'id': '97b63e2f',
        'exchange_ts': 1673576134.038,
        'order_quantity': 1,
        'cancel_quantity': 0,
        ...
    },
    'contract': {
        'code': '2890',
        'exchange': 'TSE',
        ...
    }
}
```

### OrderState.StockDeal 回呼格式

```python
{
    'trade_id': '9c6ae2eb',
    'seqno': '269866',
    'ordno': 'IN497',
    'exchange_seq': '669915',
    'action': 'Buy',
    'code': '2890',
    'order_lot': 'IntradayOdd',
    'price': 267.5,
    'quantity': 3,
    'ts': 1673577256.354
}
```

### op_type 說明

| op_type | 說明 |
|---------|------|
| New | 新單 |
| Cancel | 刪單 |
| UpdatePrice | 改價 |
| UpdateQty | 改量 |

---

## 14. 漲跌停計算

```python
# 漲停價
limit_up = api.calc_limit_up_price(
    price=contract.reference,   # 參考價
    limit_up=contract.limit_up, # 漲停百分比
    option=True                 # True=向上取整
)

# 跌停價
limit_down = api.calc_limit_down_price(
    price=contract.reference,
    limit_down=contract.limit_down,
    option=True
)
```

---

## 15. 快照

### 取得即時快照

```python
contracts = [api.Contracts.Stocks['2330'], api.Contracts.Stocks['2317']]
snapshots = api.snapshots(contracts)
```

### snapshots 簽名

```python
api.snapshots(
    contracts: List[Contract],
    timeout: int = 30000,
    cb: Callable = None,
) -> List[Snapshot]
```

### Snapshot 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| ts | int | 時間戳記 |
| code | str | 商品代碼 |
| exchange | str | 交易所 |
| open | float | 開盤價 |
| high | float | 最高價 |
| low | float | 最低價 |
| close | float | 成交價 |
| tick_type | TickType | 買賣別 {Buy, Sell} |
| change_price | float | 漲跌價 |
| change_rate | float | 漲跌率 |
| change_type | ChangeType | {Up, Down, Unchanged} |
| average_price | float | 均價 |
| volume | int | 成交量 |
| total_volume | int | 總成交量 |
| buy_price | float | 買價 |
| buy_volume | float | 買量 |
| sell_price | float | 賣價 |
| sell_volume | float | 賣量 |
| volume_ratio | float | 量比 |

### 轉 DataFrame

```python
import pandas as pd
df = pd.DataFrame(s.__dict__ for s in snapshots)
df.ts = pd.to_datetime(df.ts)
```

---

## 16. 串流行情

### 訂閱 Tick

```python
api.quote.subscribe(
    contract,
    quote_type=sj.constant.QuoteType.Tick,
    version=sj.constant.QuoteVersion.v1
)
```

### 訂閱 BidAsk

```python
api.quote.subscribe(
    contract,
    quote_type=sj.constant.QuoteType.BidAsk,
    version=sj.constant.QuoteVersion.v1
)
```

### 訂閱 Quote（完整五檔）

```python
api.quote.subscribe(
    contract,
    quote_type=sj.constant.QuoteType.Quote,
    version=sj.constant.QuoteVersion.v1
)
```

### subscribe 簽名

```python
api.quote.subscribe(
    contract: Contract,
    quote_type: QuoteType,    # {'tick', 'bidask', 'quote'}
    intraday_odd: bool = False,  # True=盤中零股行情
    version: QuoteVersion = 'v0',  # 建議用 v1
)
```

### 零股行情訂閱

```python
api.quote.subscribe(
    contract,
    quote_type=sj.constant.QuoteType.Tick,
    version=sj.constant.QuoteVersion.v1,
    intraday_odd=True   # ← 零股行情
)
# Info: TIC/v1/ODD/*/TSE/2330
```

### 取消訂閱

```python
api.quote.unsubscribe(contract, sj.constant.QuoteType.Tick, sj.constant.QuoteVersion.v1)
```

### Tick v1 回呼

```python
from shioaji import TickSTKv1, Exchange

def quote_callback(exchange: Exchange, tick: TickSTKv1):
    print(f"Exchange: {exchange}, Tick: {tick}")

api.quote.set_on_tick_stk_v1_callback(quote_callback)
```

### Tick 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| code | str | 商品代碼 |
| datetime | datetime | 時間 |
| open/close/high/low | Decimal | OHLC |
| avg_price | Decimal | 均價 |
| volume | int | 成交量 |
| total_volume | int | 累計量 |
| tick_type | int | 1=外盤, 2=內盤 |
| price_chg | Decimal | 漲跌價 |
| pct_chg | Decimal | 漲跌率 |
| intraday_odd | int | 是否零股 |

### BidAsk v1 回呼

```python
from shioaji import BidAskSTKv1, Exchange

def bidask_callback(exchange: Exchange, bidask: BidAskSTKv1):
    print(f"Exchange: {exchange}, BidAsk: {bidask}")

api.quote.set_on_bidask_stk_v1_callback(bidask_callback)
```

### BidAsk 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| code | str | 商品代碼 |
| datetime | datetime | 時間 |
| bid_price | List[Decimal] | 買價 (5檔) |
| bid_volume | List[int] | 買量 |
| diff_bid_vol | List[int] | 買價增減量 |
| ask_price | List[Decimal] | 賣價 (5檔) |
| ask_volume | List[int] | 賣量 |
| diff_ask_vol | List[int] | 賣價增減量 |
| suspend | bool | 暫停交易 |
| simtrade | bool | 試撮 |

### 事件回呼設定

```python
# 事件回呼（訂閱成功/失敗）
api.quote.set_event_callback(func)

# Tick v1 回呼
api.quote.set_on_tick_stk_v1_callback(func)

# BidAsk v1 回呼
api.quote.set_on_bidask_stk_v1_callback(func)

# Quote v1 回呼
api.quote.set_on_quote_stk_v1_callback(func)

# 通用回呼（v0 舊版）
api.quote.set_quote_callback(func)
```

---

## 17. 歷史資料

### 歷史 Tick

```python
ticks = api.ticks(
    contract=api.Contracts.Stocks["2330"],
    date="2023-01-16"
)

# Ticks(ts=[...], close=[...], volume=[...],
#        bid_price=[...], bid_volume=[...],
#        ask_price=[...], ask_volume=[...], tick_type=[...])
```

### ticks 簽名

```python
api.ticks(
    contract: BaseContract,
    date: str = '2022-12-26',
    query_type: TicksQueryType = AllDay,   # 或 RangeTime
    time_start: Union[str, time] = None,
    time_end: Union[str, time] = None,
    last_cnt: int = 0,
    timeout: int = 30000,
    cb: Callable = None,
) -> Ticks
```

### 指定時段查詢

```python
ticks = api.ticks(
    contract=api.Contracts.Stocks["2330"],
    date="2023-01-16",
    query_type=sj.constant.TicksQueryType.RangeTime,
    time_start="09:00:00",
    time_end="09:20:01"
)
```

### Ticks 欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| ts | int | timestamp |
| close | float | 成交價 |
| volume | int | 成交量 |
| bid_price | float | 委買價 |
| bid_volume | int | 委買量 |
| ask_price | float | 委賣價 |
| ask_volume | int | 委賣量 |
| tick_type | int | 1=外盤, 2=內盤, 0=無法判定 |

### 歷史 K 線

```python
kbars = api.kbars(
    contract=api.Contracts.Stocks["2330"],
    start="2023-01-15",
    end="2023-01-16"
)

# Kbars(ts=[...], Open=[...], High=[...], Low=[...], Close=[...], Volume=[...])
```

### kbars 簽名

```python
api.kbars(
    contract: BaseContract,
    start: str = '2023-01-15',
    end: str = '2023-01-16',
    timeout: int = 30000,
    cb: Callable = None,
) -> Kbars
```

### 轉 DataFrame

```python
import pandas as pd

df = pd.DataFrame({**kbars})
df.ts = pd.to_datetime(df.ts)
df.head()
```

---

## 18. 非阻塞模式

### 非阻塞下單

```python
trade = api.place_order(contract, order, timeout=0)
# status → Inactive (結果由 callback 回報)
```

### 非阻塞更新狀態

```python
api.update_status(api.stock_account, timeout=0)
```

### 非阻塞取消

```python
api.cancel_order(trade, timeout=0)
```

> `timeout=0` 表示不等待回應，結果透過 order callback 非同步回報

---

## 19. 模擬環境

```python
import shioaji as sj

api = sj.Shioaji(simulation=True)
accounts = api.login(
    person_id="PAPIUSER01",
    passwd="2222"
)

# 模擬帳號
api.stock_account
api.futopt_account
```

---

## 20. 快速入門

```python
import shioaji as sj

# 1. 初始化
api = sj.Shioaji()

# 2. 登入
accounts = api.login(api_key="KEY", secret_key="SECRET")

# 3. 啟用 CA（正式環境）
api.activate_ca(ca_path="/path/to/Sinopac.p12", ca_passwd="PASSWORD")

# 4. 取得商品檔
contract = api.Contracts.Stocks.TSE.TSE2834

# 5. 建立委託
order = api.Order(
    price=20.5,
    quantity=1,
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.Common,
    account=api.stock_account
)

# 6. 送單
trade = api.place_order(contract, order)

# 7. 更新狀態
api.update_status(api.stock_account)

# 8. 查成交
trade.status

# 9. 查快照
snapshots = api.snapshots([contract])

# 10. 登出
api.logout()
```

---

## 21. ETF 專用筆記

### OTC vs TSE 查詢

| ETF | 交易所 | 查詢方式 |
|-----|--------|----------|
| 0050 | TSE | `api.Contracts.Stocks.TSE.TSE0050` |
| 00878 | TSE | `api.Contracts.Stocks.TSE.TSE00878` |
| 00679B | OTC | `api.Contracts.Stocks.OTC.get('00679B')` |
| 00929 | TSE | `api.Contracts.Stocks.TSE.TSE00929` |

### 盤中零股下單流程

```python
# 1. 取得合約（注意 OTC 用 .get()）
contract = api.Contracts.Stocks.OTC.get('00679B')

# 2. 建立零股委託
order = api.Order(
    price=27.25,
    quantity=100,           # 股，不是張
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.IntradayOdd,
    account=api.stock_account
)

# 3. 送單
trade = api.place_order(contract, order)

# 4. 驗證（關鍵！）
api.update_status(api.stock_account)
# 確認: trade.status.status == 'Filled' 或 'Submitted'
# 確認: trade.order.ordno 有值（非空字串）
# 確認: broker_order_id 存在（非 null）

# 5. 查持倉
api.list_positions(api.stock_account)
```

### yfinance Ticker 對照

| Shioaji 代碼 | yfinance Ticker |
|-------------|-----------------|
| 0050 | 0050.TW |
| 00878 | 00878.TW |
| 00679B | 00679B.TWO |
| 00929 | 00929.TW |

---

## 22. 已知問題

### api.logout() Segfault

- 現象：`api.logout()` 後程式 crash，exit code 139
- 原因：Shioaji C 底層釋放記憶體 bug
- 影響：不影響登出功能，回傳值 True 是正常的
- 對策：在腳本結尾 `api.logout()` 後接 `sys.exit(0)` 強制退出，或忽略 exit 139

### github.io DNS 解析（IPv6）

- 現象：`sinotrade.github.io` 在某些環境 DNS 解到 IPv6，連線失敗
- 對策：`curl -4 --resolve sinotrade.github.io:443:185.199.111.153`

### ai.sinotrade.com.tw 403 Forbidden

- 現象：官方 API 網站返回 403
- 對策：使用 github.io 靜態文件，或直接查 SDK docstring

### CA 憑證路徑

- 憑證路徑從 `private/.env` 讀取（SINOPAC_CA_CERT）
- CA 密碼即 person_id（身分證字號）
- 必須先 `api.activate_ca(ca_path, ca_passwd)` 才能正式下單

---

## 常用常數速查

```python
import shioaji as sj

# Action
sj.constant.Action.Buy
sj.constant.Action.Sell

# StockPriceType
sj.constant.StockPriceType.LMT    # 限價
sj.constant.StockPriceType.MKT    # 市價
sj.constant.StockPriceType.MKP    # 範圍市價

# OrderType
sj.constant.OrderType.ROD
sj.constant.OrderType.IOC
sj.constant.OrderType.FOK

# StockOrderLot
sj.constant.StockOrderLot.Common       # 整股
sj.constant.StockOrderLot.Fixing       # 定盤
sj.constant.StockOrderLot.Odd          # 盤後零股
sj.constant.StockOrderLot.IntradayOdd  # 盤中零股

# StockOrderCond
sj.constant.StockOrderCond.Cash             # 現股
sj.constant.StockOrderCond.MarginTrading     # 融資
sj.constant.StockOrderCond.ShortSelling      # 融券

# QuoteType
sj.constant.QuoteType.Tick
sj.constant.QuoteType.BidAsk
sj.constant.QuoteType.Quote

# QuoteVersion
sj.constant.QuoteVersion.v0
sj.constant.QuoteVersion.v1

# Status (OrderStatus.status)
# PendingSubmit, PreSubmitted, Submitted, Cancelled, Filled, Failed, Inactive
```