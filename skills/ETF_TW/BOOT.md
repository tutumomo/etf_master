# ETF Dashboard Boot & Alignment Sequence

## 啟動服務 (Start Services)
若要啟動或重啟監控儀表板，請執行（**建議顯式注入 AGENT_ID**）：
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

## 技能對齊協定 (Agent Alignment Protocol)
> [!IMPORTANT]
> **給 Agent 的指令**：
> 這份 ETF_TW 已位於 Hermes profile 技能目錄，請以目前這份技能樹為主。
> 若遇到「文件已更新、dashboard 仍顯示舊版」的情況，優先檢查：
> 1. 是否重啟了正確路徑下的 dashboard
> 2. 是否誤用到歷史副本或錯誤技能路徑
> 3. 目前 active profile 是否為 `etf_master`

## 核心能力連結
- **Dashboard**: [http://localhost:5055](http://localhost:5055)
- **Intelligence**: `instances/<agent_id>/state/intraday_tape_context.json`
- **Skill Root**: `~/.hermes/profiles/etf_master/skills/ETF_TW`
