# ETF_TW Standard Cron Pack

## 目的
讓 Hermes 版 ETF_TW 在完成 `setup_agent.py` 後，可以用單一入口註冊並啟用標準 cron 任務組合，避免手動註冊造成漂移與重複。

## 核心原則
- 一鍵註冊（可 dry-run）
- dedupe 以 live cron list / 實際落地結果為準
- job 需帶 `agentId=<instance_id>`，避免跨 instance 汙染
- cron payload 禁止硬編碼環境路徑

## 標準入口
### 透過 setup_agent.py 初始化
```bash
python3 scripts/setup_agent.py --link <instance_id>
```

### Dry-run
```bash
python3 scripts/register_standard_cron_pack.py <instance_id> --dry-run true
```

### 落地註冊
```bash
python3 scripts/register_standard_cron_pack.py <instance_id> --dry-run false
```

## Pack 內容（目前）
- 盤前摘要（watchlist am）
- 盤後摘要（watchlist pm）
- 盤中 decision scan driver（每 30 分）
- 台灣市場情境 refresh（每 30 分）
- 外部事件情境 refresh（每 30 分）
- 重大事件檢查（每 30 分）
- 品質校正（15:30 交易日）
- 每日檢討（15:10 交易日）
- 每週回顧（週六 09:00）

## 驗證方式
- 實際排程系統中應可見 `agentId=<instance_id>` 的上述任務
- 每個 job metadata 應含 `dedupe_key=cronpack::<instance_id>::...`
