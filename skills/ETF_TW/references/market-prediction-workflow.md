---
name: etf-tw-market-prediction-workflow
description: 隔日台股行情預測的標準化五步流程，整合三大財經技能產出結構化預測報告
category: etf-tw
---

# 台股隔日行情預測工作流

## 觸發條件
- 使用者問「明天行情」「預測」「大盤看法」「開盤預測」
- 使用者問「下週/下月趨勢」且需要短線預測框架

## 五步流程（必須按序執行）

### Step 1：大盤技術面（stock-market-pro-tw）
```bash
cd ~/.hermes/profiles/etf_master
uv run skills/stock-market-pro-tw/scripts/yf.py report ^TWII 3mo
uv run skills/stock-market-pro-tw/scripts/yf.py report 0050.TW 3mo
```
產出：TWII + 0050 的 RSI、MACD、BB、價格位置。

### Step 2：持倉 ETF 健康度（stock-analysis-tw）
```bash
uv run skills/stock-analysis-tw/scripts/analyze_stock.py <持有ETF代碼> --fast
```
從 live query 取得持倉代碼後執行。產出：各 ETF 建議 + 信心度 + 關鍵訊號。

### Step 3：國際市場脈絡（stock-market-pro-tw + web_search）
```bash
# 注意：yf.py 的 price 子命令一次只吃一個 symbol，需逐一呼叫
uv run skills/stock-market-pro-tw/scripts/yf.py price ^GSPC
uv run skills/stock-market-pro-tw/scripts/yf.py price ^IXIC
uv run skills/stock-market-pro-tw/scripts/yf.py price ^VIX
uv run skills/stock-market-pro-tw/scripts/yf.py price TSM
```
`news.py` 若因 duckduckgo_search / ddgs 版本差異報錯（`DDGS.news() got an unexpected keyword argument 'backend'`），改用 `web_search` 補新聞摘要：
- `web_search("US stock market close summary ...")`
- `web_search("台股 明日 開盤 預測 ...")`

### Step 4：熱點與早期訊號（stock-analysis-tw）
```bash
uv run skills/stock-analysis-tw/scripts/hot_scanner.py --no-social
uv run skills/stock-analysis-tw/scripts/rumor_scanner.py
```

### Step 5：綜合預測報告
產出格式固定為：

1. **國際市場昨晚收盤摘要**（表格）
2. **台股技術面**（RSI/MACD/BB/法人動向）
3. **持倉 ETF 健康度**（表格：建議/信心度/關鍵訊號）
4. **重大事件**（法說會、政策、地緣政治）
5. **多空力量對比表**
6. **預測情境**（基準/樂觀/悲觀，各附機率%）
7. **行動建議**（表格：行動/說明）

## 關鍵規則

- ⚠️ 步驟1-4可並行（delegate_task），步驟5依賴1-4結果
- ⚠️ Yahoo Finance 對台灣 ETF 的 fundamentals 回傳 None，這是預期行為
- ⚠️ `dividends.py` 對台灣 ETF 回傳 "no dividend"，需用 yfinance 原始資料或官網補充
- ⚠️ `yf.py history` 在 NaN 資料上會崩潰，用 `pro` 替代或加 `.dropna()`
- ⚠️ 必須附上風險聲明：量化數據+技術面的機率推估，非投資保證
- 持倉資料必須從 live API 取得，不可用 state/memory 推測

## 並行加速建議

步驟1-3可以透過 delegate_task 並行執行（最多3個子任務），步驟4單獨跑（hot_scanner + rumor_scanner），步驟5由主 agent 綜合。

## ETF 供應商篩選流程

當使用者問「哪些是 X 投信操盤且績效佳」時：
1. 讀取 `instances/etf_master/state/watchlist.json` 取得完整關注清單
2. 從 live API 取得目前持倉，扣除已持有
3. 按供應商名稱篩選（ETF 名稱含供應商關鍵字）
4. 對篩選後的 ETF 執行 analyze_stock + price + history + dividends
5. 與現有持倉做重疊度分析
6. 產出比較表格（1Y報酬/殖利率/費用率/RSI/風險等級/與持倉重疊度）