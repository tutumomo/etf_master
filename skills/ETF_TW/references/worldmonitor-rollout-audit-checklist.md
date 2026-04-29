---
name: etf-tw-worldmonitor-rollout-audit
description: ETF_TW 接入 worldmonitor 後的落地驗收與缺口盤點流程（避免功能已接、鏈路未通、文件未同步）
---

# ETF_TW worldmonitor Rollout Audit

## 何時使用
- 使用者說「worldmonitor 已接入，請完整測試」
- 功能看似完成，但要確認是否真的可運作
- 要產出「評論 + 尚未落地缺口」報告

## 目標
在一次審核中同時覆蓋：
1. 功能是否可用（腳本/API/state）
2. 測試是否全綠（不是只跑局部）
3. 鏈路是否完整（警報觸發是否真的連到下游）
4. 文件與版本是否同步

## 驗收順序（固定）
1. **先盤點改動面**
   - 確認 worldmonitor 相關變更涉及：sync 腳本、dashboard API、AI 輸入、state 檔、cron、測試檔
2. **先跑 worldmonitor 專屬測試**
   - 先確定新增能力本身沒壞
3. **再跑全套測試**
   - 必須以「全套 0 failed」作為落地門檻
4. **再做實機驗證**
   - 驗證 refresh / status / snapshot 更新是否一致
5. **最後做文件一致性檢查**
   - README / CHANGELOG / SKILL 的版本與敘述是否同步

## 必查缺口（這輪實戰萃取）
1. **L3 事件下游觸發路徑**
   - watch 模式若使用錯誤相對路徑，會導致重大事件腳本未被呼叫（看似成功但實際斷鏈）
2. **輸入源序號不一致**
   - 文案常寫第13/第14不一致；應以實際 payload 鍵數為準
3. **測試硬編碼日期**
   - 送單配額/日切測試若硬編碼日期，跨日即失敗；應改用台北時區當日動態日期
4. **版本文件未同步**
   - SKILL 已升版但 README/CHANGELOG 未更新，對外發布資訊會失真
5. **worldmonitor 僅進 request、未進最終 reasoning（高機率假接線）**
   - 需同時檢查 `generate_ai_decision_request.py` 與 `generate_ai_agent_response.py`：
     - 前者是否把 worldmonitor 放入 `inputs.worldmonitor_context`
     - 後者是否真的讀取 worldmonitor 欄位參與決策理由
   - 若 request 有值但 response 邏輯無 worldmonitor 參考，判定為「鏈路只到中途，未餵到智能體」
6. **worldmonitor context schema 漂移**
   - 實作可能只輸出摘要欄位（如 `supply_chain_stress / geopolitical_risk / taiwan_strait_risk`），沒有 `snapshot` 與 `recent_alerts`
   - 驗收時不得憑文件假設鍵名，必須以當次 `ai_decision_request.json` 實際鍵值為準

## 評論輸出模板
- **整體評價**：可用 / 部分可用 / 未落地
- **已通過**：列出腳本、API、測試通過項
- **缺口分級**：P0（斷鏈）/ P1（全測試不綠）/ P2（文件或敘述一致性）
- **落地判定**：只有在 P0/P1 清零且全測試綠燈才算「完整落地」

## 實戰補充（2026-04-19）

### 1) L3 觸發腳本路徑必須用 skill root（避免雙層 `skills/ETF_TW/skills/ETF_TW`）
在 `sync_worldmonitor.py` 的 watch 模式，L3 事件觸發段應使用：
- `ROOT / '.venv' / 'bin' / 'python3'`
- `ROOT / 'scripts' / 'check_major_event_trigger.py'`
- `subprocess.run(..., cwd=str(ROOT), check=False)`

若用錯相對路徑，表面上 watch 腳本會成功結束，但重大事件下游其實沒有被觸發（假落地）。

### 2) 全測試失敗若集中在 daily quota，先檢查「測試日期是否硬編碼」
常見失敗：
- `test_daily_submit_quota_gate.py`
- `test_dashboard_daily_submit_quota.py`

根因通常是測試把 `daily_order_limits.json.date` 寫死（如 `2026-04-17`），而實作會用台北時區「今日日期」比對，跨日即被 reset。

修法：
- 測試改成 `datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()`
- `last_updated` 也改動態時間，避免跨日脆弱測試。

### 3) 若要宣告「完整落地」，建議採用嚴格門檻：0 failed + 0 warnings
這輪實務顯示：
- `tests/test_venv_executor.py` 若 `return True` 會觸發 `PytestReturnNotNoneWarning`
- 第三方 `shioaji` 的 Pydantic 相容警告可透過 `pytest.ini` 精準過濾

推薦做法：
- 測試函式僅用 `assert`，不要 `return bool`
- 新增 `pytest.ini`：只過濾第三方已知警告，不要全域靜音。

## 完成標準
- worldmonitor 專屬測試通過
- 全套測試 0 failed（建議 0 warnings）
- refresh/status/state 三方一致
- 下游觸發鏈可確認
- README / CHANGELOG / SKILL 版本與敘述一致
- **決策鏈最終落地驗證**：不能只驗 `ai_decision_request.json` 有 `inputs.worldmonitor_context`；必須再驗 `ai_decision_response.json.reasoning.risk_context_summary` 實際包含 worldmonitor 風險摘要（避免「request 有資料、agent 推理未使用」）
- **Wiki 背景非空驗證**：`wiki_context.market_view`、`wiki_context.risk_signal`、`wiki_context.entities` 需至少一項非空，且 entities 要驗證 slug 檔名匹配（`{symbol}-*.md`）
