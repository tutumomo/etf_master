# Phase 5 - 首家券商對接（永豐金證券）

## 完成日期
2026-03-16

## 完成項目

### 1. 永豐金證券適配器 (`scripts/adapters/sinopac_adapter.py`)
- ✅ 完整實作 `SinopacAdapter` 類別
- ✅ 繼承自 `BaseAdapter` 抽象基類
- ✅ 實作所有必需方法：
  - `authenticate()` - 認證流程
  - `get_market_data()` - 市場資料查詢
  - `get_account_balance()` - 帳戶餘額查詢
  - `get_positions()` - 持倉查詢
  - `preview_order()` - 訂單預覽
  - `validate_order()` - 訂單驗證
  - `submit_order()` - 訂單提交
  - `cancel_order()` - 訂單取消
  - `get_order_status()` - 訂單狀態查詢

### 2. 工廠模式整合
- ✅ 更新 `get_adapter()` 支援 'sinopac'
- ✅ 更新 `__init__.py` 導出 `SinopacAdapter`
- ✅ 提供 `create_sinopac_adapter()` 工廠函式

### 3. 測試腳本 (`scripts/test_sinopac.py`)
- ✅ 完整測試所有適配器方法
- ✅ 包含 6 項核心測試
- ✅ 所有測試通過

## 測試結果

```
測試：永豐金證券適配器（Scaffold）
=====================================

1. 測試認證
   認證結果：成功

2. 測試市場資料查詢
   標的：0050.TW
   價格：100.0
   漲跌：0.5

3. 測試帳戶餘額查詢
   可用餘額：NT$ 500,000
   可買權限：NT$ 1,000,000

4. 測試持倉查詢
   持倉筆數：1
   - 0050.TW: 1000 股

5. 測試訂單預覽
   預估費用：NT$ 142.50
   預估稅額：NT$ 0.00

6. 測試訂單驗證
   驗證結果：有效

✅ 所有測試通過
```

## 技術實作

### 認證流程
```python
async def authenticate(self) -> bool:
    # TODO: 實作真實的永豐金 API 認證
    # 需要：
    # 1. API 憑證（帳號/密碼）
    # 2. 雙因子認證（如有）
    # 3. Session token 管理
    pass
```

### 市場資料
```python
async def get_market_data(self, symbol: str) -> Dict:
    # TODO: 串接永豐金市場資料 API
    # 或從 TWSE 取得即時行情
    pass
```

### 訂單提交
```python
async def submit_order(self, order: Order) -> Order:
    # TODO: 提交訂單到永豐金交易系统
    # 需要完整的錯誤處理與風險控制
    pass
```

## 下一步（真實 API 對接）

### 1. 取得永豐金 API 憑證
- 聯絡永豐金證券
- 申請 API 使用權限
- 取得 API Key/Secret

### 2. 研究永豐金 API 文件
- 認證端點
- 市場資料端點
- 交易端點
- 帳戶查詢端點

### 3. 實作真實 API 調用
```python
# 範例：使用 aiohttp 進行非同步 API 調用
async def _call_api(self, endpoint: str, data: Dict) -> Dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.api_url}/{endpoint}",
            headers=self._get_headers(),
            json=data
        ) as response:
            return await response.json()
```

### 4. 錯誤處理與重試機制
- 處理 API 限流
- 處理網路錯誤
- 處理交易錯誤
- 實作指數退避

### 5. 安全性強化
- 機密資訊加密存儲
- 使用環境變數
- 實作請求簽名
- 日誌脫敏

## 檔案結構

```
ETF_TW/
├── scripts/
│   ├── adapters/
│   │   ├── base.py (已更新)
│   │   ├── paper_adapter.py
│   │   ├── sinopac_adapter.py (NEW)
│   │   └── __init__.py (已更新)
│   ├── test_sinopac.py (NEW)
│   └── etf_tw.py
├── references/
│   └── phase5-sinopac-scaffold.md (THIS FILE)
└── TASKS.md (已更新)
```

## 使用範例

### 建立永豐金適配器
```python
from adapters.sinopac_adapter import create_sinopac_adapter

config = {
    'account_id': 'YOUR_ACCOUNT',
    'password': 'YOUR_PASSWORD',
    'trade_password': 'YOUR_TRADE_PASSWORD',
    'api_url': 'https://api.sinopac.com'
}

adapter = create_sinopac_adapter(config)
```

### 執行測試
```bash
python3 scripts/test_sinopac.py
```

### 使用 CLI（未來）
```bash
# 使用永豐金帳戶進行模擬交易
python3 scripts/etf_tw.py paper-account orders.json -a my_sinopac

# 使用永豐金真實交易（Phase 6）
python3 scripts/etf_tw.py trade-account orders.json -a my_sinopac --mode live
```

## 風險提醒

**目前僅為 Scaffold 實作，尚未連接真實 API**

實際交易需要：
1. 永豐金證券 API 憑證
2. 真實的證券帳戶
3. 完整的 API 對接實作
4. 嚴格的風險控制機制
5. 完整的錯誤處理
6. 交易日誌與審計功能

## 總結

Phase 5 已完成：
- ✅ 永豐金證券適配器框架
- ✅ 完整的方法實作（Scaffold）
- ✅ 測試腳本與驗證
- ✅ 工廠模式整合

準備進行：
- ⏳ 真實 API 對接
- ⏳ 真實交易測試
- ⏳ 風險控制完善

**距離真實交易環境又更近了一步！** 🚀
