# ETF_TW：Hermes 版台灣 ETF 技能與 Dashboard (v1.2.1)

這是目前掛載在 Hermes profile (`etf_master`) 下的 ETF_TW 技能目錄。
它提供台灣 ETF 的研究、風控、持倉監控、state-driven dashboard，以及與券商流程對齊的交易輔助能力。

## 目前定位
- 主系統：Hermes Agent
- 技能路徑：`~/.hermes/profiles/etf_master/skills/ETF_TW`
- Dashboard：`http://localhost:5055`
- 本機狀態快照 (Level 3 Snapshot)：`instances/<agent_id>/state/`

## 啟動方式
```bash
# 推薦方式 (透過 CLI 工具)
python3 scripts/etf_tw.py dashboard --port 5055

# 手動方式 (直接啟動 uvicorn)
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

## 維運原則
1. 先確認正在執行的是 Hermes 這份 ETF_TW，而不是其他歷史副本或錯誤路徑
2. dashboard / script / state 路徑都以 Hermes 這份技能樹為主
3. 舊系統留下的教訓可以保留，但不能再把舊環境當現行主體
4. **Agent 摘要同步**：系統會自動維持 `instances/<agent_id>/state/agent_summary.json`，供 Hermes Agent 快速讀取當前決策狀態與資產概況。

## 核心功能
- ETF 查詢 / 比較 / 風險解讀
- 持倉與掛單監控
- state-driven Dashboard
- 決策引擎 / AI Bridge 對齊
- 交易前 validate / preview / pre-flight 檢查

## 注意
如果你發現：
- GitHub 拉下來的是舊版
- Hermes 與其他歷史副本各有一份 ETF_TW
- dashboard 顯示內容與你昨天看到的不一樣

先不要直接改功能，先確認目前 active 的是誰，再做修復。
