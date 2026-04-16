---
name: etf-tw-live-query
description: ETF_TW 即時持倉與掛單查詢（繞過 state 檔，直接走 live broker API）
category: etf-tw
---

# ETF_TW 即時持倉查詢

## 觸發條件
- 使用者問「持倉現況」、「掛單是否成交」、「查一下」
- 需要確認 state 檔與券商實際是否一致

## 強制回答 SOP（每次都要照做）

當使用者詢問持倉 / 掛單時，回答格式固定為：

1. 本次 live API 直接看到：
2. 本次 live API 無法確認：
3. 次級資訊（若引用 state / summary / 過往紀錄，必須明講不是本次 live 確認）
4. 建議下一步（如提供券商截圖對帳）

### 禁止事項
- 禁止把 state / summary / memory 包裝成「現在持倉」
- 禁止因為過去下過單，就直接說「現在一定已持有」
- 禁止在 live API 顯示異常時，自行挑一個版本當真相
- 禁止用推測補洞

## 正確流程（不走冤枉路）

### 1. 憑證不再用 `api_secret=`
```python
# 錯
api.login(api_key='B*2*K*AYGT...', api_secret='K*Q*...')

# 對：參數名是 secret_key
api.login(api_key='9NTj2vkuL5', secret_key='51xgnv5ZVM')
```

### 2. 憑證去哪拿？
路徑：`~/.openclaw/skills/ETF_TW/private/.env`
```bash
cat ~/.openclaw/skills/ETF_TW/private/.env
# 輸出：
# SINOPAC_API_KEY=9NTj2vkuL5
# SINOPAC_SECRET_KEY=51xgnv5ZVM
# SINOPAC_ACCOUNT=0737121
```

### 3. 正確呼叫方式：透過 Adapter（不要自己 new Shioaji）

```bash
cd ~/.openclaw/skills/ETF_TW
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python3 -c "
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from scripts.account_manager import get_account_manager

async def check():
    adapter = get_account_manager().get_adapter('sinopac_01')
    ok = await adapter.authenticate()
    print('auth:', ok)
    
    # 即時持倉
    pos = await adapter.get_positions('0737121')
    print('=== 持倉 ===')
    for p in pos:
        print(f'{getattr(p,\"symbol\",\"?\")} {getattr(p,\"quantity\",\"?\")}股')
    
    # 即時帳戶
    bal = await adapter.get_account_balance('0737121')
    print('現金:', getattr(bal,'cash_available','?'))
    
    # 真實成交單（包含 pending/failed/filled）
    trades = adapter.api.list_trades()
    print('=== 成交/掛單 ===')
    for t in trades:
        print(f'{t.id} {t.code} {t.action} {t.price}x{t.quantity} status={t.status}')

asyncio.run(check())
"
```

### 4. 注意：`list_orders()` 不存在
- 不要呼叫 `adapter.api.list_orders()`，這個方法不存在
- 正確可用的是 `adapter.api.list_trades()`
- 但也要誠實：`list_trades()` 不是完整成交歷史真相源，僅能作為當下可見訂單資訊的一部分

### 5. 為什麼 state 檔的 pending 訂單不存在？
`list_trades()` 回傳空，**不能直接推論**那張單根本沒送進券商系統。較保守的說法是：本次查詢沒有看到該訂單紀錄；可能是未送達、查詢可見性限制、或資料同步時差，需搭配 submit 回應、後續查詢與其他證據交叉驗證。

### 6. sync_live_state.py 可以強製刷新
```bash
cd ~/.openclaw/skills/ETF_TW
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python3 scripts/sync_live_state.py
# 輸出 LIVE_STATE_SYNC_OK 表示成功
```

### 7. 下單的正確方式（使用 Order dataclass）

```python
from scripts.adapters.base import Order

order = Order(
    symbol='00919',
    action='buy',
    quantity=100,
    price=22.90,
    order_type='limit',      # 'limit' 或 'market'
    account_id='0737121',
    mode='live',
    status='pending'
)
result = await adapter.submit_order(order)
print(result.status)  # 'submitted' 只表示 adapter / submit 流程回傳已送出，仍需後續驗證是否在券商側可見
```

**千萬不要**自己組 dict 然後 call `submit_order(symbol=..., action=...)` — 會爆 `TypeError`。

### 8. 掛單驗證：查無此單 ≠ 掛失敗

`list_trades()` 回傳空，只能說本次查詢沒有看到該訂單；不能直接解讀成掛失敗，也不能直接解讀成已成交。`submit_order` 的回傳 `status` 只能當 submit 階段訊號，不足以單獨證明委託已落地；仍需後續驗證與交叉比對。

## ⚠️ 真相源與限制（最重要）

### 持倉 / 掛單查詢原則
- 問「現在持倉多少、掛單是否成交」時，**先查 live broker API**，不要先引用 state / summary / memory
- 但必須誠實：Shioaji 某些查詢結果可能有單位或數量顯示異常，**live API 有時也不是足夠完整的真相源**
- 因此回覆時必須區分：
  1. 本次 API 直接看到的欄位
  2. 本次 API 無法確認的部分
  3. 來自 state / 過往紀錄的次級資訊（若提及，必須明講不是 live 確認）

### 下單單位
- `Order.quantity` 傳入單位是「股」
- 整股 / 零股轉換由 `submit_order` 內部處理
- **禁止**在回答中自行腦補「100股一定會被拒絕」；零股支援狀態必須以當前 adapter 實作為準

### 已知 API 限制
- `list_orders()` **不存在**，只能用 `list_trades()`
- `list_trades()` 對已完成訂單的可見性有限，**不能單靠它斷言所有成交歷史都完整可見**
- `list_positions()` 曾出現數量顯示異常；若結果和使用者既有券商畫面衝突，必須明說「本次 API 無法可靠確認」，不要擅自選一個版本當真相

## 重要教訓
- **不要**直接 `shioaji.Shioaji()` + login，會繞過 adapter 的 simulation mode 邏輯
- **永遠**透過 `get_account_manager().get_adapter()` 取 adapter
- **永遠**設定 `OPENCLAW_AGENT_NAME` 環境變數，否則會拿到別人的設定
- State / summary / memory **都不是 live truth**，不能拿來冒充當下券商事實
- 下單一律用 `Order` dataclass，不要用 dict/kwargs
- 當 live API 也不可靠時，要直接承認「目前無法確認」，不要用推測補洞
