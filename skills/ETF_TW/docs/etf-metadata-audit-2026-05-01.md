# ETF 基本資料體檢報告 — 2026-05-01

## 結論

ETF_TW 的台股 ETF **廣度已補齊到官方全市場 338 檔**，並已修正 TWSE 雙幣別 ETF 被合併成怪代號的問題。全市場基本欄位與衍生 profile 欄位目前都是 100% 完整。

深度資料分成兩層：

- `data/etf_universe_tw.json`：全市場廣度與標準化基本欄位，應作為交易代號驗證與全市場搜尋的 truth source。
- `data/etfs.json` / wiki：高觸碰 curated 深度資料，目前只覆蓋核心標的，應優先補 watchlist / holdings，而不是一次產生 338 檔深度敘述。

## 官方來源

- TWSE listed ETFs: `https://www.twse.com.tw/rwd/zh/ETF/list?response=json`
- TPEx ETFs: `https://info.tpex.org.tw/api/etfFilter`

## 本次補強

- 更新 `sync_etf_universe_tw.py`：
  - TWSE `<br>` 多幣別列拆成獨立 symbol。
  - 例如 `006205(新臺幣)<br>00625K(人民幣)` 拆成 `006205` 與 `00625K`。
  - 主動式 ETF 無追蹤指數時標準化為 `主動式 ETF（無追蹤指數）`。
  - 新增 `issuer_short`、`asset_class`、`region`、`strategy_tags`、`risk_flags`、`currency`、`yfinance_ticker`。
- 新增 `audit_etf_metadata.py`：
  - 固定輸出 `data/etf_metadata_audit.json`。
  - 檢查廣度、核心欄位、衍生欄位、curated 深度與 wiki 覆蓋。
- 同步 `wiki/raw/data/etf_universe_tw.json`，保持 clone 後知識庫也能取得最新 universe。

## 體檢數字

| 指標 | 結果 |
|---|---:|
| 全市場 ETF universe | 338 |
| TWSE | 224 |
| TPEx | 114 |
| malformed symbols | 0 |
| core fields completeness | 338 / 338 = 100% |
| derived profile completeness | 338 / 338 = 100% |
| curated 深度檔 | 7 |
| curated 深度完整率 | 7 / 7 = 100% |
| wiki entity 覆蓋 | 16 / 338 |

## 分布

### 資產類別

| 類別 | 檔數 |
|---|---:|
| equity | 206 |
| bond | 112 |
| currency | 10 |
| commodity | 7 |
| real_estate | 3 |

### 區域

| 區域 | 檔數 |
|---|---:|
| Taiwan | 97 |
| US | 81 |
| Other | 80 |
| China/HK | 33 |
| Global/Emerging | 28 |
| Japan | 11 |
| Europe | 5 |
| India | 3 |

### 發行商 Top 10

| 發行商 | 檔數 |
|---|---:|
| 元大 | 54 |
| 富邦 | 50 |
| 國泰 | 43 |
| 群益 | 27 |
| 台新 | 21 |
| 復華 | 20 |
| 中國信託 | 20 |
| 凱基 | 17 |
| 中信 | 15 |
| 永豐 | 12 |

## 已驗證案例

- `00720B` 現可由 universe 查到：
  - 名稱：元大投資級公司債
  - 交易所：TPEx
  - yfinance ticker：`00720B.TWO`
  - asset_class：bond
  - strategy_tags：`long_duration_bond`
  - risk_flags：`duration_risk`
- 主動式 ETF 搜尋可查到 29 檔。
- 雙幣別 ETF 已拆分：
  - `006205` / `00625K`
  - `00636` / `00636K`

## 仍保留的深度缺口

`data/etfs.json` 的人工 curated 深度資料只有 7 檔，這不是交易驗證缺口，但會影響 dashboard / beginner flow 的解說深度。

建議下一步只補 **watchlist + holdings** 的 curated 深度欄位，不建議補滿 338 檔，原因是費用率、AUM、配息頻率會變動，若沒有官方自動來源，人工補滿會很快失準。

優先補齊名單：

`0050`, `0056`, `006208`, `00679B`, `00687B`, `00713`, `00720B`, `00694B`, `00830`, `00878`, `00892`, `00919`, `00922`, `00923`, `00929`, `00935`, `00939`, `00940`

## 判定

- 廣度：PASS。
- 基本欄位深度：PASS。
- 交易代號驗證：PASS。
- 高觸碰標的 curated 解說：PARTIAL，建議列入下一輪資料深度補強。
