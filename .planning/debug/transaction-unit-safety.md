---
status: resolved
trigger: "針對「交易單位安全」進行專項跑測與除錯。目標：驗證用戶在 Dashboard 輸入「100股」買入時，從前端傳遞到後端、再到 Adapter 的過程中，是否存在被誤判為「100張」的可能。"
created: 2025-05-22T10:00:00Z
updated: 2025-05-22T10:30:00Z
---

## Current Focus

hypothesis: "前端傳遞的 quantity 可能在後端或 Adapter 中被誤解為「張」而不是「股」，或者在轉換為 SDK 參數時沒有正確處理零股（IntradayOdd）與整股（Common）的邏輯。"
test: "閱讀 dashboard/app.py, scripts/adapters/base.py, scripts/adapters/sinopac_adapter.py 並編寫測試腳本模擬 100 股的下單流程。"
expecting: "代碼中應有明確的單位轉換邏輯，且 100 股應被識別為 IntradayOdd。"
next_action: "已完成修復與驗證。"

## Symptoms

expected: "用戶輸入 100 股，系統應以 100 股（零股）下單。"
actual: "已修復。原本下單 100 股會被誤判定為 1 張 (1000 股)。"
errors: "無崩潰但存在嚴重邏輯誤區。"
reproduction: "使用 100 股進行 paper-trade 或透過 Dashboard 提交。"
started: "專項檢查。"

## Eliminated

## Evidence

- timestamp: 2025-05-22T10:15:00Z
  checked: skills/ETF_TW/scripts/adapters/sinopac_adapter.py 中的 _submit_order_impl 方法
  found: 存在嚴重的單位轉換邏輯錯誤。代碼將所有小於 1000 股的訂單強制轉換為 lots=1，且未設定 order_lot 參數。
  implication: 這意味著用戶下單 100 股時，系統會以「整股 (Common)」模式下單 1 張 (1000 股)，導致用戶買入 10 倍的數量。此外，即使是真正的零股單，因為 quantity 被設為 1，用戶也只會買到 1 股而非 100 股。

## Resolution

root_cause: SinopacAdapter._submit_order_impl 中缺乏正確的整股/零股判定邏輯，誤將「張」與「股」混淆，且漏掉 Shioaji API 必需的 order_lot 參數。此外，BaseAdapter 預設將所有訂單標記為 board lot，導致 100 股訂單在風控閘門就被阻斷。
fix: 
- 修正 SinopacAdapter._submit_order_impl：新增自動判定邏輯。若數量不是 1000 的倍數，設為 StockOrderLot.IntradayOdd 且數量保持為「股」；若是 1000 的倍數，設為 StockOrderLot.Common 且數量轉換為「張」。同時確保零股訂單強制使用 LMT 限價。
- 修正 BaseAdapter.submit_order：根據數量自動判定 lot_type（1000 股以上為 board，以下為 odd），以正確通過 pre_flight_gate 的單位檢查。
- 修正匯入路徑：解決部分相對匯入在腳本模式下運作失敗的問題。
verification: 編寫測試腳本模擬 100 股與 2000 股下單，確認送到 Shioaji SDK 的參數完全符合台股「盤中零股」與「整股」的規範。
files_changed: [skills/ETF_TW/scripts/adapters/base.py, skills/ETF_TW/scripts/adapters/sinopac_adapter.py]
