# ETF_TW 核心邏輯審查報告 (REVIEW.md)

---
phase: 02-code-review
reviewed: 2024-05-23T10:30:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - scripts/pre_flight_gate.py
  - scripts/adapters/base.py
  - scripts/generate_decision_consensus.py
  - skills/stock-analysis-tw/scripts/analyze_stock.py
findings:
  critical: 1
  warning: 6
  info: 4
  total: 11
status: issues_found
---

## 1. 交易保險絲：pre_flight_gate.py 審查

**核心問題：集中度計算邏輯存在重大偏差。**

### WR-01: 集中度計算未考慮現有持倉 (Sizing Logic Error)
**File:** `scripts/sizing_engine_v1.py:27`
**Issue:** `base_amount` 的計算公式為 `(cash * max_concentration_pct) * risk_temperature`。這僅計算了「可用現金」的佔比，而非「總資產」的佔比。更嚴重的是，它完全沒檢查用戶是否已經持有該標的。
**Risk:** 若用戶總資產 100 萬，已持有 30 萬 0050（已達 30% 上限），但手邊還有 50 萬現金。此邏輯會允許再買入 `50 * 0.3 = 15 萬` 的 0050，導致最終集中度變為 45%，繞過風控。
**Fix:** 應傳入 `total_portfolio_value` 與 `current_holding_value`。
```python
# 建議修正方向
total_value = cash + current_inventory_value
max_allowed_value = total_value * max_concentration_pct
available_quota = max(0, max_allowed_value - current_holding_value)
limit_amount = min(available_quota, max_single_limit_twd) * risk_temperature
```

### WR-02: 交易時段檢查缺乏休市日意識
**File:** `scripts/trading_hours_gate.py:34`
**Issue:** 僅檢查 `now.weekday() >= 5`（週末），未對接台灣證交所休市日（農曆年、國定假日）。
**Risk:** 在休市日執行自動化腳本時，若 `force_trading_hours=True`，閘門會失效或誤判。
**Fix:** 應引入 `holidays` 庫或維護一個 `tw_market_holidays` 清單。

### IN-01: 缺少漲跌幅限制檢查
**File:** `scripts/pre_flight_gate.py`
**Issue:** 未檢查 `price` 是否超過昨日收盤價的 ±10%。雖然券商端會擋，但在 Pre-flight 階段若能先擋，可優化 UI 反饋。

---

## 2. 真相層級：BaseAdapter 審查

**核心問題：基類方法可被覆蓋導致風控繞過。**

### WR-03: `submit_order` 缺乏 final 修飾 (Bypass Risk)
**File:** `scripts/adapters/base.py:126`
**Issue:** `submit_order` 包含了核心的 `check_order` 閘門與 `verify_order_landing` 落地驗證。然而，這是一個普通方法，子類（如 `SinopacAdapter`）可以覆蓋它。
**Risk:** 若開發者為了方便，在子類中直接實現 `async def submit_order(...)` 而非 `_submit_order_impl`，將完全繞過保險絲與真相層級檢查。
**Fix:** 在文檔中明確規定禁止覆蓋 `submit_order`，或改用裝飾器模式強制執行。

### WR-04: 落地驗證依賴 list_trades 的及時性
**File:** `scripts/submit_verification.py:44`
**Issue:** 落地驗證通過輪詢 `list_trades()` 確認訂單。若券商 API 延遲同步（超過 10 秒），訂單會被標記為 `LEVEL_2_VERIFYING` (未落地/待確認)。
**Info:** 這雖然不是 Bug，但會造成系統狀態長期停留在「不確定」區間，影響後續 AI 決策。
**Fix:** 建議增加延遲重試機制或掛載 Callback 處理。

---

## 3. 決策仲裁：generate_decision_consensus.py 審查

**核心問題：對外部資料讀取的健壯性極低。**

### CR-01: 缺少 JSON 解析異常處理 (Crash Risk)
**File:** `scripts/generate_decision_consensus.py:17`
**Issue:** 直接調用 `json.loads(RULE_STATE_PATH.read_text(...))`。若 `auto_trade_state.json` 為空、不存在（雖然有判斷 exists 但沒判斷內容）或損壞，腳本會拋出 `JSONDecodeError` 並崩潰。
**Risk:** 決策中樞崩潰會導致整個交易流水線中斷，控制台無法產出最新的 `decision_consensus.json`，Dashboard 顯示過期資訊。
**Fix:** 增加 `try...except json.JSONDecodeError`。

### WR-05: 缺乏資料新鮮度檢核 (Stale Data)
**File:** `scripts/generate_decision_consensus.py`
**Issue:** 仲裁邏輯未檢查 `ai_decision_response.json` 的 `timestamp`。
**Risk:** 若 AI 服務當機，AI 訊號停留在三天的「BUY」，而今日規則引擎發出「SELL」，系統可能因 arbitrate 邏輯誤判為「意見分歧」而錯失避險時機。
**Fix:** 應檢查文件修改時間或 JSON 內的 timestamp，超過一定時間（如 4 小時）則將該訊號標記為 `EXPIRED/INVALID`。

### IN-02: 決策識別過於簡略
**File:** `scripts/generate_decision_consensus.py:10`
**Issue:** 使用 `"buy" in summary` 進行模糊匹配。若 AI 輸出「Do not buy yet」，會被誤判為 `BUY`。
**Fix:** 應強制要求 AI 輸出特定 Enum 格式。

---

## 4. 多技能路徑：analyze_stock.py 審查

**核心問題：併發寫入與寫入路徑競爭。**

### WR-06: 狀態文件競爭寫入 (Race Condition)
**File:** `skills/stock-analysis-tw/scripts/analyze_stock.py:2550`
**Issue:** 腳本執行「讀取 -> 修改 -> 覆蓋寫入」`stock_intelligence.json`。
**Risk:** 若 `etf_tw` 在分析 A 標的同時，另一個進程在分析 B 標的，且兩者都指向相同的 `--state-dir`，後完成的進程會覆蓋掉先完成進程的數據（Lost Update）。
**Fix:** 寫入時應使用文件鎖（File Locking）或將每個標的寫入獨立的文件（如 `{ticker}.json`）。

### IN-03: 權限與原子寫入問題
**File:** `skills/stock-analysis-tw/scripts/analyze_stock.py:2565`
**Issue:** 直接 `open(..., "w")` 寫入。若寫入過程中磁碟滿載或進程被終止，會導致 JSON 文件毀損。
**Fix:** 應先寫入臨時文件，再進行 `os.replace`。

### IN-04: 市場指標偏差 (Market Bias)
**File:** `skills/stock-analysis-tw/scripts/analyze_stock.py:365`
**Issue:** `analyze_market_context` 使用 `^VIX`, `SPY`, `QQQ` 等美股指標。
**Info:** 雖然全球市場相關，但對於 ETF_TW 而言，這對於台股短線情緒的捕捉可能存在時間差。
**Fix:** 建議增加台股專屬指標（如台指期、台股 VIX 指數）。

---
_Reviewed: 2024-05-23_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
