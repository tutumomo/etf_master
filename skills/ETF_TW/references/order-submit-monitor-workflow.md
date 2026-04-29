---
name: etf-tw-order-submit-monitor
description: 完整下單流程：報價 → 取得確認 → 送單 → 驗證 → 設定限時自動監控 cron（只在交易時段運行，有結果主動通知）
category: etf-tw
---

# ETF_TW 下單 + 成交監控 SOP

## 核心原則
1. **送單前**：先給報價 + 完整委託內容讓用戶確認
2. **送單時**：用 Order dataclass + SinopacAdapter.submit_order()
3. **送單後**：立刻寫入 orders_open.json
4. **驗證**：手動執行一次 order_monitor.py 確認腳本正常
5. **監控**：設定 cron job，只在交易日 9:00-13:30 運行，有成交主動通知用戶

---

## Step 1：送單前報價

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW && .venv/bin/python3 -c "
import yfinance as yf
ticker = yf.Ticker('[CODE].TW')
hist = ticker.history(period='5d', interval='1d')
for idx, row in hist.iterrows():
    print(f'{idx.strftime(\"%m/%d\")} 開:{row[\"Open\"]:.2f} 高:{row[\"High\"]:.2f} 低:{row[\"Low\"]:.2f} 收:{row[\"Close\"]:.2f} 量:{int(row[\"Volume\"]):,}')
"
```

---

## Step 2：取得用戶確認（罐頭格式）

```
■ 報價 — [代號][名稱]

| 日期 | 開 | 高 | 低 | 收 | 成交量 |
|------|----|----|----|----|--------|

■ 委託確認（待你回覆確認後才送單）

| 項目 | 內容 |
|------|------|
| 代號 | [CODE] |
| 動作 | 買入/賣出 |
| 數量 | [N] 股 |
| 限價 | [PRICE] TWD |
| 總金額 | [AMOUNT] TWD |

> ⚠️ 目前帳戶現金 [CASH] TWD，掛單後餘額約 [REMAINING] TWD。

確認無誤？回「確認」後立即送單。
```

---

## Step 3：正式送單

```python
# 使用 Order dataclass + SinopacAdapter
from scripts.account_manager import get_account_manager
from scripts.adapters.base import Order

async def submit():
    manager = get_account_manager()
    adapter = manager.get_adapter('sinopac_01')
    await adapter.authenticate()

    order = Order(
        symbol='[CODE]',
        action='buy',           # 'buy' 或 'sell'
        quantity=[N],
        price=[PRICE],
        order_type='limit',
        account_id='0737121',
        mode='live',
        status='pending'
    )
    result = await adapter.submit_order(order)
    print('result:', result)
```

---

## Step 4：更新 orders_open.json

```json
{
  "orders": [
    {
      "order_id": "[BROKER_ORDER_ID]",
      "symbol": "[CODE]",
      "action": "buy",
      "quantity": [N],
      "price": [PRICE],
      "mode": "live",
      "status": "submitted",
      "observed_at": "[TIMESTAMP]",
      "verified": true,
      "broker_order_id": "[BROKER_ORDER_ID]",
      "broker_status": "submitted",
      "account": "sinopac_01",
      "broker_id": "sinopac"
    }
  ],
  "updated_at": "[TIMESTAMP]",
  "source": "live_broker"
}
```

路徑：`~/.hermes/profiles/etf_master/skills/ETF_TW/state_legacy_compat_link/orders_open.json`

---

## Step 5：設定成交監控 cron（兩層保護）

### 5a. 確認腳本存在並正常

```bash
# 手动执行一次确认脚本工作正常
cd ~/.hermes/profiles/etf_master/skills/ETF_TW && .venv/bin/python3 ~/.hermes/scripts/order_monitor.py
```

### 5b. 設定 Cron Job

**重要：要用 cron expression 控制時段，不要用 `every 30m`（會在休市時繼續跑）**

```bash
# 平日 9:00-13:30，每 30 分鐘觸發一次
# 格式：*/30 9-13 * * 1-5
```

用 cronjob tool 設定：
- schedule: `*/30 9-13 * * 1-5`
- repeat: 99（或足夠撐到收盤的次數）
- script: `order_monitor.py`
- deliver: `telegram:[USER_CHAT_ID]`
- prompt: 包含職責說明、執行方式、終止條件

---

## 腳本邏輯要求（必須內含）

```python
def is_trading_hours():
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return time(9, 0) <= t <= time(13, 30)

# 超出時段 → 直接終止
if not is_trading_hours():
    print("已過交易時段，監控終止")
    print("HERMES_CRON_TERMINATE=true")
    return
```

---

## 常見失敗點

| 問題 | 原因 | 解法 |
|------|------|------|
| `Invalid character '*'` | API Key/Secret 有 `*` 遮罩字元 | 從 `~/.hermes/profiles/etf_master/skills/ETF_TW/private/.env` 讀取真實金鑰 |
| `submit_order() got unexpected keyword` | 用了 dict 而非 Order dataclass | 用 `Order(symbol=..., action=..., ...)` |
| `quantity must be 1000 的倍數` | 舊腳本/舊規則把零股誤判為非法 | 這是過時規則；應改查當前 adapter 的 `order_lot` 實作，整股走 Common，零股走 IntradayOdd / Odd |
| `submitted` 就被當成已掛單 | 把 submit 回應誤當委託落地 | `submitted` 只能算 submit 階段訊號；必須再用 broker order id / 後續查詢 / 其他證據交叉驗證 |
| `list_trades()` 查不到就判定失敗或已成交 | 把查詢空值過度解讀 | 正確說法只能是「本次查詢沒看到」；可能是可見性限制、同步時差或未送達 |
| `集保賣出庫存不足` | 買入尚未T+2交割入庫，或真的沒股票 | 賣出前先確認 `get_positions()` 有持股 |
| 休市還在跑 cron | cron 語法沒有綁定時段 | 改用 `*/30 9-13 * * 1-5` 而非 `every 30m` |

## 2026-04-14 補充硬規則
- submit attempt 與 verified landing 必須分開記錄；不能因為跑過 submit 就把 `not_submitted=False`。
- Shioaji quantity 單位必須跟 `order_lot` 一起看：
  - `Common` → quantity 用「張」
  - `IntradayOdd` / `Odd` → quantity 用「股」
- 任何監控或回報文案都不能把「已送出 submit」寫成「已正式掛單」。
- 問持倉 / 掛單時，回答至少要分成：本次 live API 直接看到、無法確認、次級資訊。

---

## 監控腳本位置

`~/.hermes/scripts/order_monitor.py`

（第一次需要建立，之後下單直接更新 ORDERS dict 內的內容）
