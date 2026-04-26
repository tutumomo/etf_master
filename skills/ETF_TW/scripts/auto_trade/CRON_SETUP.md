# Phase 2 自動交易 — cron 安裝指引

本文件說明如何把 Phase 2 自動交易（半自動）的兩個排程腳本掛上 macOS。

## 兩個排程任務

| 腳本 | 頻率 | 用途 |
|------|------|------|
| `scripts/sync_intraday_quotes.py` | 每分鐘（交易時段內） | 抓 yfinance 1m K 線，寫 `intraday_quotes_1m.json` |
| `scripts/auto_trade_scan.py`      | 每分鐘（交易時段內） | 觸發買賣掃描；過期清理；13:30 同步 peak_tracker |

兩者**獨立運作**——sync 寫資料，scan 讀資料。`auto_trade_scan` 內部會
自動判斷現在是否在 09:30 / 11:00 / 13:00 / 13:15 觸發窗 ± 5 分鐘內，
不在時點窗內就只跑「過期清理」。

## 上線檢查清單（重要！）

依序確認後再開 master switch：

- [ ] **驗證所有單元測試通過**：
      ```bash
      cd ~/.hermes/profiles/etf_master/skills/ETF_TW
      PYTHONPATH=. .venv/bin/python -m pytest tests/test_vwap_calculator.py \
          tests/test_pending_queue.py tests/test_circuit_breaker.py \
          tests/test_buy_scanner.py tests/test_peak_tracker.py \
          tests/test_sell_scanner.py tests/test_pre_flight_gate.py
      ```
      預期：128 passed
- [ ] **手動跑一次 sync_intraday_quotes**：確認能抓到資料
- [ ] **手動跑一次 auto_trade_scan**：確認沒有 import / state 錯誤
- [ ] **dashboard 看到 Phase 2 卡片**：master switch 顯示「🔴 未啟用」
- [ ] **熔斷器 7 個檢查全綠**（除了 master_switch）
- [ ] **掛上 cron 但維持 master switch 關閉**：跑 1–2 個交易日觀察 history
- [ ] **history 正常後再開 master switch**

## macOS cron 設定（推薦）

編輯 crontab：

```bash
crontab -e
```

加入這兩行（請把路徑改為你自己的）：

```cron
# Phase 2 自動交易：盤中報價同步（交易日 09:00–13:30 每分鐘）
* 9-13 * * 1-5 cd /Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3 scripts/sync_intraday_quotes.py >> /tmp/etf_sync_intraday.log 2>&1

# Phase 2 自動交易：買賣掃描 + 過期清理（同上時段）
* 9-13 * * 1-5 cd /Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3 scripts/auto_trade_scan.py >> /tmp/etf_auto_trade_scan.log 2>&1
```

注意：
- `* 9-13` = 每小時的每分鐘，9-13 點（含 13:00–13:59）
- `1-5` = 週一到週五
- `AGENT_ID=etf_master` 必須設，否則 ETF_TW 找不到 instance state
- log 寫到 /tmp，可隨時 `tail -f /tmp/etf_auto_trade_scan.log` 觀察

## 啟動 / 停止

**啟用 Phase 2**：在 dashboard 點 master switch 打勾即可。

**緊急停止**：
1. **dashboard 直接關 master switch**（最快，cron 仍跑但所有掃描跳過）
2. **或 `crontab -e` 註解掉兩行**（cron 不再執行）
3. **或刪除 pending queue**：
   ```bash
   rm ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/pending_auto_orders.json
   ```

## state 檔案清單

cron 啟動後會產生/更新以下檔案：

| 檔案 | 內容 | 由誰寫 |
|------|------|--------|
| `intraday_quotes_1m.json` | 盤中 1m K 線 | sync_intraday_quotes.py |
| `pending_auto_orders.json` | 等 ack 訊號 | buy/sell_scanner |
| `auto_trade_history.jsonl` | 所有訊號歷史 | enqueue / status_change |
| `position_peak_tracker.json` | 持倉 peak_close | peak_tracker.sync_with_positions |
| `position_cooldown.json` | 賣出 7 天冷卻 | sell_scanner.write_sell_cooldown |
| `auto_trade_circuit_breaker.json` | 熔斷器最近狀態（選用） | circuit_breaker.save_state |
| `auto_trade_phase2_config.json` | master switch + 自訂閾值 | dashboard /api/auto-trade/phase2/config |

## 故障排除

### sync_intraday_quotes.py 抓不到資料

- yfinance 對台股約 15 分鐘延遲，09:00 跑可能還沒有資料
- 09:30 後通常都有
- 確認網路：`curl https://query1.finance.yahoo.com/v8/finance/chart/0050.TW`

### auto_trade_scan.py 跑了但沒訊號

正常情況——只有滿足以下三個條件才會產生訊號：
1. cron 在觸發窗內（09:30 / 11:00 / 13:00 / 13:15 ± 5min）
2. master switch = enabled
3. 至少一檔標的跌幅 ≥ 1%（買入）或 < stop_price（賣出）

### dashboard 看不到 pending

- 檢查 `pending_auto_orders.json` 內容
- pending 是「未過期且 status='pending'」的，已過期會在 list_active 中過濾掉
- 重新整理頁面（Phase 2 card 內建每 30 秒輪詢，但只是 console.log 提示）

## 上線後監控建議

每天收盤後檢查：

```bash
# 看 history 最近 20 筆
tail -20 ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/auto_trade_history.jsonl | python3 -m json.tool

# 看 peak_tracker
cat ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/position_peak_tracker.json | python3 -m json.tool

# 看 cron log
tail -50 /tmp/etf_auto_trade_scan.log
```
