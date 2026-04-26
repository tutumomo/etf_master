# ETF_TW：Hermes 版台灣 ETF 技能與 Dashboard (v1.5.0)

這是目前掛載在 Hermes profile (`etf_master`) 下的 ETF_TW 技能目錄。
它提供台灣 ETF 的研究、風控、持倉監控、state-driven dashboard、Phase 2 半自動交易，以及與券商流程對齊的交易輔助能力。

## 目前定位
- 主系統：Hermes Agent
- 技能路徑：`~/.hermes/profiles/etf_master/skills/ETF_TW`
- Dashboard：`http://localhost:5055`
- 本機狀態快照 (Level 3 Snapshot)：`instances/<agent_id>/state/`

## Multi-instance 環境變數契約（新安裝必做）
- `AGENT_ID`：Hermes 現行主鍵（**必填**）
- `OPENCLAW_AGENT_NAME`：legacy fallback（相容舊腳本，非新安裝主設定）

```bash
# 建議：在所有入口顯式注入
AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py search 0050
```

## 啟動方式
```bash
# 推薦方式 (透過 CLI 工具)
AGENT_ID=etf_master python3 scripts/etf_tw.py dashboard --port 5055

# 手動方式 (直接啟動 uvicorn)
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

## 維運原則
1. 先確認正在執行的是 Hermes 這份 ETF_TW，而不是其他歷史副本或錯誤路徑
2. dashboard / script / state 路徑都以 Hermes 這份技能樹為主
3. 舊系統留下的教訓可以保留，但不能再把舊環境當現行主體
4. **Agent 摘要同步**：系統會自動維持 `instances/<agent_id>/state/agent_summary.json`，供 Hermes Agent 快速讀取當前決策狀態與資產概況。

## 核心功能
- ETF 查詢 / 比較 / 風險解讀
- 持倉與掛單監控（含分群配置比例視覺化、現金三層揭露）
- state-driven Dashboard（衝突歷史、策略影響力、感測器降級指引）
- 決策引擎 / AI Bridge 對齊（Tier 1/2/3 共識）
- graphify 知識圖譜查詢 + llm-wiki 長期沉澱
- worldmonitor 全球風險雷達（daily/watch 快照 + 事件警報）
- 交易前 validate / preview / pre-flight 檢查（以「可交割金額」管控 sizing）
- **Phase 2 半自動交易**：09:30/11:00/13:00 VWAP 跌幅階梯買入 + 13:15 trailing stop 賣出 → 訊號入 pending queue → 使用者 ack 才下單

## Phase 2 半自動交易

訊號掃描排程（macOS launchd，每分鐘執行）：

| 觸發時點 | 動作 |
|---------|------|
| 09:30 / 11:00 / 13:00 ± 5min | 對 watchlist 算前 30 分鐘 VWAP，跌幅階梯（−1%→2k / −2%→4k / −3%→6k / −4%→8k / ≥−5%→10k TWD）→ pre_flight_gate → pending queue |
| 13:15 ± 5min | 持倉 trailing stop（core 6% / income 5% / defensive 4% / other 8%；報酬 ≥20% 鎖利收緊到 3%）→ pending queue（市價單）|
| 13:30 ± 5min | 同步 peak_tracker（每日收盤後）|
| 每分鐘 | 過期清理（TTL 15 分鐘） |

7 項 Circuit Breaker 熔斷檢查（任一失敗即擋下）：
master_switch / market_risk / major_event / sensor_health / weekly_loss / consecutive_buy_days / daily_buy_amount

**啟動方式**：
1. 載入 launchd job：`launchctl load ~/Library/LaunchAgents/com.etf_master.{sync_intraday,auto_trade_scan}.plist`
2. 在 dashboard「Phase 2 自動交易」卡片打開 master switch
3. 訊號出現時 → 按「✅ 確認下單」或「❌ 拒絕」，否則 15 分鐘自動作廢

**緊急停止**：dashboard 直接關 master switch（cron 仍跑但所有掃描跳過），或 `launchctl unload`。

詳見 `scripts/auto_trade/CRON_SETUP.md`。

## 版本紀錄

### v1.5.0 (2026-04-26)
- feat(auto_trade): 完成 Phase 2 半自動交易系統 🎉
  - M1：盤中報價基礎建設（VWAP 計算、`sync_intraday_quotes.py`）
  - M2：買入掃描 + pending queue + 7 項 circuit breaker 熔斷
  - M3：trailing stop 賣出掃描 + peak tracker（群組 trailing %、≥20% 鎖利）
  - M4：Dashboard pending card + ack/reject 流程 + launchd 排程
- feat(gate): 「單筆金額上限」改以可交割金額為基準（cash − T+1/T+2）
- feat(dashboard): 多項 UI 強化
  - P1-1 衝突歷史面板（Tier 2/3 規則 vs AI 分歧）
  - P1-2 策略影響力即時摘要（對齊率、勝率）
  - P1-3 感測器降級行動指引
  - P2-4 持倉分群配置比例 bar
  - P2-5 事件堆積警報
  - 現金 KPI 三層揭露（帳面 / 可交割 / 待交割）
- fix(ohlcv): `return_1y` 不再因台股交易日 < 252 一律 None，改用年化推算
- 累計 128 個新 unit test（總計 555/555 PASS）

### v1.4.17 (2026-04-24)
- feat(dashboard): 「現金 / 追蹤數」卡片新增交割安全金額顯示
- feat(live-state): Full Sync 同步時一併查詢 `api.settlements(api.stock_account)`，寫入 T+1/T+2 淨交割款與 `settlement_safe_cash`
- ux(dashboard): 現金卡片顯示 T+1/T+2 淨額，避免只看帳面現金誤判可動用金額
- test(live-state): 補交割安全金額計算回歸測試

### v1.4.16 (2026-04-24)
- fix(dashboard): 修復預覽交易 API 500，補齊 `trade_preview()` 缺失的 state context / JSON loader 接線
- feat(dashboard): 預覽交易評分接入 AI 信心來源；當前 AI 候選標的使用 `ai_decision_response`，其他標的使用透明的 per-symbol `ai_bridge_heuristic`
- ux(dashboard): 預覽面板新增「評分因子」與「AI 信心來源」顯示，避免把 heuristic 誤看成真 AI 判斷
- chore(context): AGENT_ID warning 改為 process-local 說明，明確區分互動 shell 已設與非互動 subprocess 未帶入的情況

## 注意
如果你發現：
- GitHub 拉下來的是舊版
- Hermes 與其他歷史副本各有一份 ETF_TW
- dashboard 顯示內容與你昨天看到的不一樣

先不要直接改功能，先確認目前 active 的是誰，再做修復。
