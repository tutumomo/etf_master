# ETF_TW 增強功能使用指南

## 更新日期：2026-03-26

今日已立即補強以下功能，**無需等待永豐審核**：

---

## ✅ 功能 1：漲跌停檢查

### 功能說明
在下單前自動檢查訂單價格是否超過漲跌停限制，避免無效委託。

### 使用方式

```python
from scripts.adapters.sinopac_adapter_enhanced import SinopacAdapterEnhanced

# 建立適配器
adapter = SinopacAdapterEnhanced('sinopac', {
    'api_key': 'YOUR_API_KEY',
    'secret_key': 'YOUR_SECRET_KEY',
    'mode': 'live'
})

# 登入
await adapter.authenticate()

# 檢查漲跌停
result = await adapter.check_price_limits('0050', 76.0)
print(f"參考價：{result['reference']}")
print(f"漲停：{result['limit_up']}")
print(f"跌停：{result['limit_down']}")
print(f"有效：{result['valid']}")
print(f"警告：{result['warnings']}")
```

### 輸出範例
```
參考價：76.2
漲停：83.8
跌停：68.6
有效：True
警告：[]
```

### 自動檢查時機
- 使用 `validate_order()` 時會自動檢查
- 也可單獨調用 `check_price_limits()` 進行檢查

---

## ✅ 功能 2：訂單驗證（含漲跌停）

### 功能說明
增強版訂單驗證，包含：
- 基本驗證（帳戶、標的、數量）
- 漲跌停檢查
- 零股提醒
- 價格偏離警告

### 使用方式

```python
from scripts.adapters.base import Order

# 建立訂單
order = Order(
    symbol='0050',
    action='buy',
    quantity=1000,
    price=76.0
)

# 驗證訂單
valid, messages = await adapter.validate_order(order)

if valid:
    print("✅ 驗證通過")
else:
    print("❌ 驗證失敗")
    for msg in messages:
        print(f"  - {msg}")
```

### 驗證規則
- ✅ 價格在漲跌停範圍內
- ✅ 價格偏離參考價不超過 10%
- ✅ 數量為正數
- ⚠️ 非整股交易（零股）會發出警告

---

## ✅ 功能 3：成交回報回調框架

### 功能說明
註冊回調函數，在訂單狀態異動時自動通知。

### 使用方式

```python
# 定義回調函數
def my_order_callback(api, order, status):
    print(f"訂單狀態異動：{order}")
    print(f"狀態：{status}")

# 註冊回調
adapter.on_order_complete(my_order_callback)

# 下單後，回調會自動觸發
order = await adapter.submit_order(order)
```

### 應用場景
- 即時通知成交結果
- 記錄交易日誌
- 觸發後續操作（如停損/停利）

---

## ⚠️ 功能 4：交易限額查詢（需審核通過）

### 說明
此功能需要永豐審核通過後才能使用。

```python
limits = await adapter.query_trade_limits()

if limits['can_query']:
    print(f"買入限額：{limits['buy_limit']}")
    print(f"賣出限額：{limits['sell_limit']}")
else:
    print(f"備註：{limits['error']}")
    # 輸出：備註：查詢失敗：'Shioaji' object has no attribute 'query_trade_limit'
```

**現狀**：Shioaji 未提供此 API，需等待官方實作。

---

## 完整範例

```python
import asyncio
from scripts.adapters.sinopac_adapter_enhanced import SinopacAdapterEnhanced
from scripts.adapters.base import Order

async def main():
    # 1. 建立適配器
    adapter = SinopacAdapterEnhanced('sinopac', {
        'api_key': 'YOUR_API_KEY',
        'secret_key': 'YOUR_SECRET_KEY',
        'mode': 'live'
    })
    
    # 2. 登入
    if not await adapter.authenticate():
        print("登入失敗")
        return
    
    # 3. 建立訂單
    order = Order(
        symbol='0050',
        action='buy',
        quantity=1000,
        price=76.0
    )
    
    # 4. 驗證訂單（自動檢查漲跌停）
    valid, messages = await adapter.validate_order(order)
    
    if not valid:
        print("❌ 訂單驗證失敗")
        for msg in messages:
            print(f"  - {msg}")
        return
    
    print("✅ 訂單驗證通過")
    
    # 5. 下單
    result = await adapter.submit_order(order)
    print(f"訂單狀態：{result.status}")

# 執行
asyncio.run(main())
```

---

## 進階用法

### 1. 檢查極端價格
```python
# 檢查漲停價
result = await adapter.check_price_limits('0050', 85.0)
print(result['warnings'])  # ['價格 85.0 超過漲停價 83.8']

# 檢查跌停價
result = await adapter.check_price_limits('0050', 65.0)
print(result['warnings'])  # ['價格 65.0 低於跌停價 68.6']
```

### 2. 批量驗證
```python
orders = [
    Order(symbol='0050', action='buy', quantity=1000, price=76.0),
    Order(symbol='006208', action='buy', quantity=1000, price=172.0),
]

for order in orders:
    valid, messages = await adapter.validate_order(order)
    if valid:
        print(f"✅ {order.symbol} 驗證通過")
    else:
        print(f"❌ {order.symbol} 驗證失敗：{messages}")
```

---

## 注意事項

1. **價格更新**：漲跌停價格每日更新，請在交易時間內使用
2. **參考價來源**：使用 Shioaji API 提供的參考價
3. **零股提醒**：非 1000 整數倍會發出警告
4. **審核狀態**：帳務相關功能需等待永豐審核通過

---

## 錯誤排除

| 錯誤 | 原因 | 解決方法 |
|-----|------|---------|
| `未認證` | 未登入或登入失敗 | 確認 API Key 正確 |
| `找不到合約` | 標的代號錯誤 | 確認代號格式（如 0050） |
| `查詢失敗：'Shioaji' object has no attribute 'query_trade_limit'` | 交易限額 API 尚未實作 | 等待永豐審核通過 |

---

**更新日期**: 2026-03-26  
**版本**: v1.1 (增強版)
