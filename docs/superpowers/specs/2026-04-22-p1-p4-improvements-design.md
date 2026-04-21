# Design: P1–P4 系統改進

Date: 2026-04-22

## P1 — 決策品質閉環：門檻自動校正

### 問題
`BUY_THRESHOLD_BY_RISK` 在 `run_auto_decision_scan.py` 中 hardcode，`generate_decision_quality_weekly.py` 產出的 `chain_breakdown` 勝率資料從未被反饋回門檻設定。

### 實作
新增 `scripts/auto_calibrate_thresholds.py`，三層機制：

1. **建議式**：計算各 `risk_temperature` 的建議調整，永遠寫入 `state/calibration_suggestion.json`
2. **硬閾值自動套用**：rule_engine `win_rate < 40%` 且樣本 `≥ 10` → 門檻 `+0.5`；`win_rate ≥ 60%` → 門檻 `-0.5`；單次上限 `MAX_STEP=0.5`，受 `THRESHOLD_BOUNDS` 約束不越界
3. **Audit trail**：每次執行（含無動作）append 到 `state/calibration_audit.jsonl`（不可刪）

套用後的門檻存於 `state/calibrated_thresholds.json`，`run_auto_decision_scan.py` 未來可讀此檔覆蓋 hardcode 預設值。

`generate_decision_quality_weekly.py` 週報流程末尾加入 `calibrate()` 呼叫（try/except 保護，不影響週報成功與否）。

### 測試
`tests/test_auto_calibrate_thresholds.py` — 17 tests，覆蓋：
- 樣本不足 / win_rate=None 不觸發
- 低勝率觸發收緊、高勝率觸發放寬
- 調整幅度不超過 MAX_STEP
- 邊界 clamping（上限/下限不越界）
- `load_current_thresholds` 的 fallback 與部分檔案處理

---

## P2 — CLAUDE.md Multi-instance 操作參考

### 問題
`etf_master_wife` instance 已建立，但 CLAUDE.md 沒有並排啟動的快速指令，日常操作靠 DEPLOYMENT.md 查閱。

### 實作
在 `CLAUDE.md` 的 Common Commands 區塊新增 `# Multi-instance` 小節，包含：
- 兩個 instance 並排啟動指令（`AGENT_ID` + `DASHBOARD_PORT`）
- 各 instance 的 `verify_deployment.sh` 呼叫範例

---

## P3 — Wiki 主寫層統一（symlink 方案）

### 問題
`wiki/`（profile）和 `skills/ETF_TW/wiki/`（skill）各自維護相同 4 頁，容易分歧。

### 實作
- **Profile wiki** (`wiki/`) 為主寫層，直接編輯此處
- Skill wiki 4 頁（`investment-strategies.md`、`market-view.md`、`risk-signal.md`、`undervalued-etf-ranking.md`）改為 symlink，相對路徑 `../../../wiki/<file>`
- `market-view.md`、`risk-signal.md`、`undervalued-etf-ranking.md` 原只存在於 skill wiki，已移植到 profile wiki
- CLAUDE.md Key File Locations 更新說明

### 驗證
`diff` 確認 4 個 symlink 解析正確，兩端內容完全一致。

---

## P4 — stock-market-pro-tw 技術指標 contract tests

### 問題
`stock-market-pro-tw/scripts/yf.py` 的純函數（`calc_rsi`、`calc_macd`、`calc_bbands`）無任何測試，改動靜默失效。

### 實作
新增 `skills/stock-market-pro-tw/scripts/test_yf_indicators.py` — 22 tests：

- `_has_data`：空/NaN/None/正常 Series
- `calc_rsi`：輸出長度、值域 0–100、warm-up NaN、純下跌趨勢、純上漲全 NaN（loss=0 → pd.NA 的已知行為）
- `calc_macd`：三欄位存在、histogram = macd - signal、warm-up NaN、上漲 MACD > 0
- `calc_bbands`：upper ≥ mid ≥ lower、warm-up NaN、mid = rolling mean、較大 n_std 帶寬更寬、固定價格帶寬為零

**執行方式**：使用 ETF_TW venv（內含 pytest/pandas/numpy），chart 依賴（plotille、mplfinance、rich、matplotlib）以 stub 模組繞過。

```bash
cd skills/stock-market-pro-tw/scripts
~/.hermes/profiles/etf_master/skills/ETF_TW/.venv/bin/python3 -m pytest test_yf_indicators.py -v
```

---

## 測試結果摘要

| 測試檔 | 通過 | 失敗 |
|--------|------|------|
| `ETF_TW/tests/` (全套) | 381 | 4（既有） |
| `test_auto_calibrate_thresholds.py` (新增) | 17 | 0 |
| `test_yf_indicators.py` (新增) | 22 | 0 |
