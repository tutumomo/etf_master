# ETF_TW 使用說明文件 (USAGE.md)

`ETF_TW` 是一個功能強大的台灣 ETF 投資助理，支援從研究、試算到模擬交易與實盤對接的全流程。本文件詳述各關鍵指令的使用方式。

## 1. 基礎查詢指令

### `list`
列出系統精選的 ETF 清單（包含分類、配息頻率等中繼資料）。
```bash
python scripts/etf_tw.py list
```

### `search <關鍵字>`
搜尋特定 ETF。支援代碼、名稱或摘要關鍵字。
```bash
python scripts/etf_tw.py search 0050
```

### `compare <代碼1> <代碼2>`
橫向比較兩檔 ETF 的成本（費用率）、風險等級、配息頻率與適合對象。
```bash
python scripts/etf_tw.py compare 0050 006208
```

---

## 2. 試算與分析

### `calc <代碼> <每月金額> <投資年數>`
執行定期定額 (DCA) 投資複利試算。
- `--annual-return`: 假設年化報酬率（預設 0.06）。
```bash
python scripts/etf_tw.py calc 0050 10000 10 --annual-return 0.08
```

### `portfolio`
查看當前投資組合的概覽。
- 自動計算平均成本、未實現損益、總報酬率。
- 支援模擬 (Paper) 與實盤 (Live) 模式切換顯示。
```bash
python scripts/etf_tw.py portfolio
```

---

## 3. 交易相關指令

### `mode <status|paper|live>`
查詢或切換交易模式。
- `status`: 查看當前有效模式與帳戶連線狀態。
- `paper`: 切換至模擬交易模式（預設）。
- `live`: 切換至實盤模式（需完成 Pre-flight 檢查）。
```bash
python scripts/etf_tw.py mode status
python scripts/etf_tw.py mode paper
```

### `paper-trade`
執行模擬交易。
```bash
# 手動下單
python scripts/etf_tw.py paper-trade --symbol 0050 --side buy --quantity 100 --price 185
# 從檔案批量下單
python scripts/etf_tw.py paper-trade --file data/sample_orders.json
```

### `orders` 與 `list-trades`
查看委託清單與成交歷史。
- `--account`: 指定帳戶別名。
```bash
python scripts/etf_tw.py orders
python scripts/etf_tw.py list-trades --account sinopac_01
```

---

## 4. 帳戶與券商管理

### `accounts`
列出所有已配置的帳戶及其狀態（模式、別名、預設值）。
```bash
python scripts/etf_tw.py accounts
```

### `switch-account <別名>`
切換預設使用的帳戶。
```bash
python scripts/etf_tw.py switch-account sinopac_01
```

### `health`
執行指定帳戶的連線與權限檢查。
```bash
python scripts/etf_tw.py health --account my_account
```

---

## 5. 全市場 (Universe) 指令

### `universe-sync`
同步台灣交易所 (TWSE/TPEx) 的最新 ETF 代碼表。
```bash
python scripts/etf_tw.py universe-sync
```

### `universe-list` / `universe-search`
在全市場範圍內列出或搜尋標的。
```bash
python scripts/etf_tw.py universe-list --exchange TWSE
python scripts/etf_tw.py universe-search 高股息
```

---

## 6. 系統維護

### `check` / `init`
環境檢查與初始化。
- `--install-deps`: 自動安裝缺失套件。
```bash
python scripts/etf_tw.py check --install-deps
python scripts/etf_tw.py init
```
