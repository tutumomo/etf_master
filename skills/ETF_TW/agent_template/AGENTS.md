# AGENTS.md

## 開機引導
1. 讀取 SOUL.md
2. 讀取 IDENTITY.md
3. 執行 BOOT.md

## 🚨 交易時段硬約束（所有衍生智能體必須遵守）
- **一般盤**：09:00 - 13:30
- **盤後零股**：13:40 - 14:30
- **收到下單指令時，第一優先確認現在是否在交易時段**
- **若非交易時段，直接回覆「現在非交易時段，無法下單」，不得嘗試送單**

## 🛠️ 儀表板維護 (Dashboard Maintenance)
若要啟動或重啟監控後台，請在終端機執行：
`cd ~/.hermes/profiles/etf_master/skills/ETF_TW && .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055`
[儀表板存取位址](http://localhost:5055)
