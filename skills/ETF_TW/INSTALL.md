# ETF_TW 技能安裝 / 對齊說明（Hermes 版）

## 適用對象
這份文件適用於 Hermes Agent 環境，不包含任何舊系統安裝步驟。

## 目前預期位置
```bash
~/.hermes/profiles/etf_master/skills/ETF_TW
```

## 快速確認
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
pwd
```

## 建立虛擬環境
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/etf_core/requirements.txt
```

## 啟動 Dashboard
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

## 驗證
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5055/
curl -s -o /dev/null -w "%{http_code}" http://localhost:5055/api/overview
```

## 核心原則
- 這份技能以 Hermes profile 目錄為主
- `instances/<agent_id>/state/` 是正式本機狀態快照 (Level 3 Snapshot)
- 若同機器仍殘留其他 ETF_TW 歷史副本，請視為封存資料，不應當作目前主系統

## 更新方式
若這份技能已納入 git：
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
git status
git pull --rebase
```

## 文件範圍
本文件只描述 Hermes 版 ETF_TW 的對齊與啟動；不再提供任何舊系統專用步驟。
