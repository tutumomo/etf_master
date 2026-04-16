---
name: Shioaji 張股單位地雷
type: concept
tags: [Shioaji, 張, 股, 單位, Bug, 永豐]
created: 2026-04-14
updated: 2026-04-14
references: [taiwan-etf-trading.md, shioaji.md]
---

# Shioaji 張股單位地雷

## 事件摘要（2026-04-14）

| 項目 | 內容 |
|------|------|
| 發生時間 | 2026-04-14 下午 |
| 根本原因 | `sinopac_adapter.py` L445 數量轉換邏輯錯誤 |
| 事故金額 | ~217,454 TWD（T+2 4/16 扣款）|
| 受影響訂單 | 00919（意圖100股→實發1000股）、006208（意圖5股→實發1000股）|

## 原始錯誤程式碼

```python
# sinopac_adapter.py L445（旧版）
lots = order.quantity // 1000 if order.quantity >= 1000 else 1
```

**問題**：
- 當 `order.quantity = 100`（股）時，因為 `100 >= 1000` 為 `False`
- Python 三元表達式取 `else 1`，即 `lots = 1`（1 張 = 1000 股）
- 結果：100 股被當成 **1000 股**送出，金額爆增 10 倍

## 修復後的正確邏輯

```python
# sinopac_adapter.py L444-453（新版）
if order.quantity <= 0:
    order.status = 'rejected'
    order.error = '數量必須 > 0'
    return order
# 零股（不足1張）直接以 quantity=1 送出，券商接受 odd-lot
lots = order.quantity // 1000
if order.quantity % 1000 != 0:
    lots = 1  # 零股：券商視為1筆 odd-lot 委托
```

**驗證結果**：

| 輸入（股） | lots（張）| 結果 |
|------------|-----------|------|
| 100 | 1（零股）| submitted ✅ |
| 500 | 1（零股）| submitted ✅ |
| 1000 | 1（整股）| submitted ✅ |
| 2000 | 2（整股）| submitted ✅ |

## 為何這個 Bug 危險

1. **靜默失敗**：Shioaji 不會拒絕 100 股，它直接升成 1 張送出
2. **無任何錯誤訊息**：API 回傳 `submitted`，看起來一切正常
3. **數量差異 10 倍**：對零股投資者而言是**災難性錯誤**
4. **帳面掩護**：T+2 前帳面餘額看起來正常，損失在 T+2 才暴露

## 防範原則

### 對 Shioaji
- 永遠不要相信 `list_trades()` 會即時更新（已成交的單會消失）
- 永遠不要相信 `quantity < 1000` 時 API 會自動拒绝
- T+2 前帳面餘額**不是**可用現金

### 對 ETF_TW 系統
- 任何改動下單邏輯後，**必須**用真實 API 驗證（100股、500股、1000股）
- `submit_order` 的張股轉換必須有**單元測試**覆蓋
- Zero-quantity rejection 不能有 else-branch 默默升級數量

## 受影響的系統範圍

| 檔案 | 函數 | 風險 |
|------|------|------|
| `sinopac_adapter.py` | `submit_order()` | ✅ 已修復 |
| `sinopac_adapter.py` | `get_order_status()` | ⚠️ 需審計（L553 數量回傳）|
| `sinopac_adapter.py` | `validate_order()` | ⚠️ 零股行為不一致（警告 vs 阻擋）|

---

*本頁為 ETF_Master 內部教訓文件，依據 TOMO 實際事故建立，2026-04-14*
