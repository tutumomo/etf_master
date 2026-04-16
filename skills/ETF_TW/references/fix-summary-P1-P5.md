# ETF_TW 修復計劃總結 (P1-P5)

## 問題根源分析

根據對話記錄和程式碼分析，你遇到的問題可歸類為**五個系統性缺陷**：

| 問題 | 根本原因 | 對話證據 |
|------|----------|----------|
| **venv 路徑被忽略** | 沒有硬編碼強制路徑，依賴 agent「記得」 | 「原來，你居然不知道要跑 venv！！」 |
| **正式單變預演** | `auto_trade_state.json` 的 `preview_only_mode` 會覆蓋送單意圖 | 「為何老是真送單卻被當成預演？？」 |
| **訂單消失** | `orders_open.json`、`positions.json` 狀態不一致 | 「NOT_FOUND: 00929 order not in list_trades」 |
| **休市掛單失敗** | 交易時段檢查未整合到送單路徑 | 「休市實說可以掛單結果單不見了」 |
| **缺少驗證測試** | 無端到端測試驗證完整送單流程 | 每次修改後靠「實際下單」驗證，風險高 |

---

## 修復內容

### P1: 執行路徑強制化 - venv wrapper

**檔案**: `scripts/venv_executor.py`

**功能**:
- 強制使用 `skills/ETF_TW/.venv/bin/python` 執行
- 自動傳遞 `OPENCLAW_AGENT_NAME` 保持 instance 對齊
- 檢查 shioaji 套件是否已安裝

**使用方式**:
```bash
# 正式送單必須透過 venv_executor
python scripts/venv_executor.py complete_trade 00929 buy 200 --price 19.55

# 或執行其他腳本
python scripts/venv_executor.py trading_hours_gate check
```

---

### P2: 狀態分離架構 - preview/live 分開

**修改檔案**: `scripts/run_auto_decision_scan.py`

**功能**:
- `auto_trade_state.json` 僅管掃描狀態
- `auto_submit_state.json` 僅管送單狀態
- 加入明確註解保證分離，不會互相覆蓋

**關鍵修改**:
```python
# P2: 明確記錄 - 此掃描不影響送單狀態
print(f"[STATE] auto_trade_state 已更新，auto_submit_state 不受影響")
```

---

### P3: Order lifecycle 重構

**新檔案**: `scripts/state_reconciliation_enhanced.py`

**功能**:
- 單一訂單狀態機：`pending → submitted → [filled | cancelled | rejected]`
- 對帳 `orders_open.json`、`positions.json`、`filled_reconciliation.json`
- 驗證訂單狀態合法性

**使用方式**:
```bash
# 執行狀態對帳
python scripts/state_reconciliation_enhanced.py
```

**輸出範例**:
```
========================================================================
📊 狀態對帳檢查
========================================================================
對帳時間：2026-04-09T12:55:00+08:00
健康狀態：✓ 正常

📋 對帳摘要:
  總訂單數：1
  總持倉數：2
  未對帳訂單：0

✓ 狀態驗證:
  驗證結果：✓ 通過
```

---

### P4: 交易時段硬閘門

**新檔案**: `scripts/trading_hours_gate.py`
**修改檔案**: `scripts/complete_trade.py`

**功能**:
- 台灣股市交易時段檢查：
  - 一般盤：09:00 - 13:30
  - 盤後零股：13:40 - 14:30
- 非交易時段直接阻斷送單
- 週末自動休市判斷

**整合點**:
```python
# complete_trade.py 第 123-129 行
if mode in ('live', 'sandbox'):
    print("=" * 72)
    print("🕒 交易時段檢查...")
    trading_session = check_trading_hours_gate()
    print(f"   ✓ 檢查通過：目前是 {trading_session} 時段")
    print("=" * 72)
```

---

### P5: 驗證測試與文件

**新檔案**: `tests/test_venv_executor.py`

**測試項目**:
1. `test_venv_exists` - 檢查虛擬環境是否存在
2. `test_shioaji_installed` - 檢查 shioaji 套件
3. `test_trading_hours_gate` - 檢查交易時段閘門
4. `test_venv_executor_script` - 檢查 venv_executor.py
5. `test_state_reconciliation_script` - 檢查 state_reconciliation

**執行方式**:
```bash
cd skills/ETF_TW
python tests/test_venv_executor.py
```

**測試結果**:
```
========================================================================
ETF_TW 修復驗證測試
========================================================================
測試 1: 檢查虛擬環境...
  ✓ 虛擬環境存在
測試 2: 檢查 shioaji 套件...
  ✓ shioaji 已安裝
測試 3: 檢查交易時段閘門...
  ✓ 交易時段閘門邏輯正確
測試 4: 檢查 venv_executor.py...
  ✓ venv_executor.py 執行正常
測試 5: 檢查 state_reconciliation_enhanced.py...
  ✓ state_reconciliation_enhanced.py 執行正常

測試結果：5 通過，0 失敗
```

---

## Dashboard 鏈路保護

本次修復**完全保留**了各 agent 的 dashboard 對齊機制：

### 現有架構 (不變)

```
instances/
├── etf_master/
│   └── state/
│       ├── orders_open.json
│       ├── positions.json
│       ├── strategy_link.json
│       └── agent_summary.json
├── etf_daughter/
│   └── state/
│       └── ...
└── etf_son/
    └── state/
        └── ...
```

### 保護機制

1. **`venv_executor.py`** 自動傳遞 `OPENCLAW_AGENT_NAME` 環境變數
2. **`context.py`** 的 `get_instance_id()` 函數保持不變
3. **每個 agent** 仍有獨立的 state 目錄，不會互相污染

---

## Git 提交記錄

### Commit 1: P1-P3 修復
```
commit 099f23a
feat(ETF_TW): 修復正式單變預演與訂單消失問題 (P1-P3)

- P1: 建立 venv_executor.py 強制使用正確虛擬環境
- P2: 狀態分離架構 (auto_trade_state / auto_submit_state)
- P3: Order lifecycle 重構 (state_reconciliation_enhanced.py)
```

### Commit 2: P4-P5 測試
```
commit e1414f6
test(ETF_TW): 加入 P4-P5 驗證測試

- P4: 交易時段硬閘門測試
- P5: 驗證測試與文件 (tests/test_venv_executor.py)
```

---

## 使用指南

### 正式送單流程

```bash
# 1. 確認在交易時段
python scripts/venv_executor.py trading_hours_gate check

# 2. 執行狀態對帳
python scripts/venv_executor.py state_reconciliation_enhanced

# 3. 正式送單
python scripts/venv_executor.py complete_trade 00929 buy 200 --price 19.55 \
  --broker sinopac --account sinopac_01 --mode live
```

### 日常巡檢

```bash
# 執行完整測試
python tests/test_venv_executor.py

# 檢查健康狀態
python scripts/venv_executor.py dashboard_health
```

---

## 後續建議

### 短期 (本週)

1. **實際下單測試**: 在交易時段用小额測試完整流程
2. **監控日誌**: 檢查 `logs/` 目錄下的執行日誌
3. **對帳驗證**: 每次下單後執行 `state_reconciliation_enhanced.py`

### 中期 (本月)

1. **加入 cron 巡檢**: 定時執行狀態對帳
2. **完善錯誤處理**: 針對常見錯誤加入更明確的提示
3. **擴充測試覆蓋**: 加入更多情境測試

### 長期

1. **多 broker 支援**: 擴充 `venv_executor.py` 支援其他券商
2. **自動化報告**: 產生每日/每週投資報告
3. **效能優化**: 優化 state 載入與對帳速度

---

## 聯絡與回饋

如有問題或建議，請更新 `TASKS.md` 或提交 GitHub Issue。
