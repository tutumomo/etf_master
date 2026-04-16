### 教訓33：Shioaji submit_order 張/股與 odd-lot 地雷
- 舊 bug：`lots = qty // 1000 if qty >= 1000 else 1` 會把 100 股錯送成 1 張
- 後來又踩過反向錯：把所有非1000倍數都 hard reject，這同樣是錯的，因為會誤殺零股
- 正確原則：Order.quantity 以股為單位；整股/零股與 order_lot 必須由 adapter 依當前實作處理，不能靠 agent 口頭心算或舊記憶下結論
- 對外回答時，禁止再說「非1000倍數一定拒絕」這種過時規則
§
### 教訓26+27：Error 88
- 帳戶現金 8,900 TWD，Shioaji 顯示 500,000 是信用額度
- 失敗訂單自動 Failed，無需 cancel_order
§
### 教訓28：Context Summary 不能當事實
- 聲稱 Y08WJ/Y08JI 兩單已下，但 log 全 DNS 錯誤，live API 查不到
- 以後：任何「已成功下單」必須 terminal 查 live API 驗證
§
### 教訓 19：雙決策共識仲裁架構已實作
- `run_auto_decision_scan.py` 新增 `resolve_consensus()` 函數
- 三層仲裁：Tier1=一致(high), Tier2=不一致規則引擎優先(medium/low), Tier3=方向衝突鎖定(low)
- 規則引擎有否決權，AI Bridge 只能加強不能推翻
- consensus 欄位寫入 `auto_preview_candidate.json`
- mode 標記：preview-only(Tier1), preview-low-confidence(Tier2 low), preview-locked(Tier3)
- AI Bridge stale 時 → Tier2 (AI 無回應=hold，降級但規則引擎仍可執行)
- 已通過 7 場景 unit test + 模擬驗證
§
§
### 教訓 20：推薦引擎偏誤 — 00679B 永遠唯一候選
- 根因：defensive 群只有 00679B 一檔，沒有競爭者
- 計分公式缺陷：(1) 未持有+2 太粗暴 (2) 完全沒有估值/績效/動能指標 (3) 市場情境長期 elevated→defensive 永遠加分
- TOMO 的買入三原則：1.價值被低估 2.前景看好 3.過往紀錄良好 — 目前公式三個都沒有
- 修復方向：A.快補=加 defensive 候選+調分 B.重寫=加殖利率/動能/夏普值維度
- decide_action() 在 run_auto_decision_scan.py L234-363
- 門檻：score >= 4 且 side=buy 才推薦
§
§
§
### 教訓22+24：市場情境從真實數據推算+決策鏈重檢
- config/generate/rerun後自動觸發_run_consensus_rescan()
- A1✅ market_event_context v2：RSI/MACD/SMA/BB推算breadth→regime（不再硬編碼）
- A2✅ market_context_taiwan v2：量化評分(-5~+5)→regime/tilts，含quant_indicators區塊
- A3🔲 decide_action()仍缺殖利率/動能/夏普值維度
- A4🔲 reasoning仍為空字串
- shioaji API斷網仍可用（連Sinopac伺服器），volume_ratio/change_rate可用
§
### 教訓26+27：Error 88 (投資上限) 真正原因+技能重學觸發
- Error 88 根因：帳戶真實餘額8,900 TWD，Shioaji顯示500,000可用額度但只是信用額度
- 帳戶未開通完整電子下單功能，必須聯繫券商處理，無法用API參數繞過
- `api.account_balance().acc_balance` = 真實現金；Shioaji內部額度 != 實際可買
- 失敗訂單 Shioaji 會自動標 Failed，無需手動 cancel_order
- 技能：接任務先主動搜相關 skills（如 github-pr-workflow 忘了 load 代價慘重）
§
### 教訓32：持倉/掛單查詢必須誠實分層
- dashboard 是 TOMO 看的事實，但回答時不能把 state/summary/memory 包裝成 live truth
- 每次被問持倉/掛單/成交，第一動作：先查 dashboard 或 live API
- 回答固定分成：1) 本次 live API 直接看到 2) 本次 live API 無法確認 3) 次級資訊（非 live）
- shioaji list_positions()/list_trades() 可能不完整；不足以確認時必須直接說無法確認，不准用推測補洞
§
ETF_TW 穩定化計劃書已存至 /Users/tuchengshin/wiki/projects/etf-tw-stabilization-plan-for-code-agent.md，準備交給 Gemini CLI 執行。TOMO 選擇 Gemini CLI 是因為省錢。