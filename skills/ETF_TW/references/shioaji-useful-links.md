# Shioaji Useful Links and Notes

## 目的
整理從 Shioaji 社群資訊中提取、可重複查用的官方連結與高價值備忘，供 ETF_TW 後續開發、查證與排障時快速引用。

> 只保存公開且可重複驗證的官方連結與通用判讀，不保存聊天雜訊、個人資料或一次性口語內容。

---

## 官方入口
- 官方文件首頁：
  - https://sinotrade.github.io/zh/
- 前置準備總入口：
  - https://sinotrade.github.io/zh/tutor/prepare/
- API 委託下單同意書 / 測試流程相關：
  - https://sinotrade.github.io/zh/tutor/prepare/terms/
- 快速入門：
  - https://sinotrade.github.io/zh/tutor/quick_start/
- Snapshot 文件：
  - https://sinotrade.github.io/zh/tutor/market_data/snapshot/

---

## 市場資料查詢備忘
### 1. snapshots
適合一次性查詢當下行情，不一定要先訂閱即時行情。

範例：
```python
snapshots = api.snapshots([api.Contracts.Stocks["2330"]])
```

備忘：
- 一次最多 500 檔
- 流量限制：50 次 / 5 秒
- 適合用於 dashboard / 手動查價 / 快照式驗證

### 2. ticks
適合查當天或歷史逐筆成交。

範例：
```python
ticks = api.ticks(api.Contracts.Stocks["2330"], date="2026-03-27")
```

### 3. kbars
適合取得歷史 K 線。

範例：
```python
kbars = api.kbars(api.Contracts.Stocks["2330"], start="2026-03-01", end="2026-03-27")
```

---

## 401 / 權限 / 憑證相關備忘
若遇到 401，優先檢查：

1. 是否已啟用 CA 憑證
```python
api.activate_ca(ca_path="/path/to/Sinopac.pfx", ca_passwd="YOUR_PASSWORD")
```

2. API Key 權限是否已開啟 Trading
3. 下單帳戶是否指定正確
   - 股票：`api.stock_account`
   - 期貨：`api.futopt_account`
4. 是否已完成官方 API 測試流程與同意書簽署
5. 若登入正常但送單 401，考慮 token 過期，先重新登入再測試

參考連結：
- https://sinotrade.github.io/zh/tutor/prepare/terms/

---

## 模擬測試備忘
模擬測試重點：
- 測試不一定需要 CA 憑證
- 建議在交易日 08:00 ~ 20:00（台灣時間）進行
- 使用 Shioaji 1.2 以上版本
- 用模擬模式：
```python
api = sj.Shioaji(simulation=True)
```
- 證券與期貨應分開測試
- 需先完成 API 委託下單同意書簽署

參考連結：
- https://sinotrade.github.io/zh/tutor/prepare/terms/

---

## 切換正式環境備忘
模擬測試通過後，切換正式環境的核心動作：

1. 確認已完成 API 委託下單同意書簽署
2. 確認已完成 API 測試流程
3. 登入時移除 `simulation=True`
```python
api = sj.Shioaji()
api.login(api_key="YOUR_KEY", secret_key="YOUR_SECRET")
```
4. 若要下單，需啟用 CA 憑證
```python
api.activate_ca(ca_path="/path/to/Sinopac.pfx", ca_passwd="YOUR_PASSWORD")
```
5. 確認帳戶 `signed=True` 再視為正式交易可用

參考連結：
- https://sinotrade.github.io/zh/tutor/prepare/terms/

---

## 環境建議備忘
社群建議的環境方向：
- Python 3.10 ~ 3.12
- 可用 `uv` 管理環境

示意：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv init my-trading --package
cd my-trading
uv add shioaji
```

> 此段作為環境建議備忘，不代表 ETF_TW 必須改用 uv。
