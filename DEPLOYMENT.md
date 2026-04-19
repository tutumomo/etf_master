# ETF_Master 部署指南

> **目標讀者**：首次從 git clone 部署本專案的工程師。
> **前提假設**：已熟悉 Python、終端機操作、永豐金帳號（選填）。

---

## 系統需求

| 項目 | 需求 |
|---|---|
| Python | **3.14+**（ETF_TW venv 強制要求） |
| uv | 最新版（`pip install uv` 或 `brew install uv`） |
| Hermes Agent | v0.9.0+（`pip install hermes-agent`） |
| 作業系統 | macOS / Linux |
| 網路 | 需能存取 Yahoo Finance、永豐金 API（live 模式）、worldmonitor（選填） |

---

## 步驟一：Clone 與確認目錄結構

```bash
git clone <repo_url> ~/.hermes/profiles/etf_master
cd ~/.hermes/profiles/etf_master
```

預期目錄結構：
```
etf_master/
├── SOUL.md                  # Agent 人格定義
├── config.yaml              # Hermes Agent 設定
├── cron/jobs.json           # 排程任務
├── wiki/                    # 知識庫
└── skills/ETF_TW/           # 核心交易技能
    ├── SKILL.md
    ├── scripts/
    ├── dashboard/
    ├── data/
    ├── tests/
    ├── instance_config.json.example   ← 範本
    └── private/.env.example           ← 範本
```

---

## 步驟二：建立 Python 虛擬環境

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW

# 建立 venv（必須用 Python 3.14+）
python3.14 -m venv .venv

# 啟動 venv
source .venv/bin/activate

# 安裝依賴
pip install -r scripts/etf_core/requirements.txt

# 驗證核心套件
.venv/bin/python3 -c "import yfinance, pandas, numpy, shioaji, fastapi, uvicorn; print('OK')"
```

> **重要**：所有正式指令都必須用 `.venv/bin/python3`，不要用系統 Python。

---

## 步驟三：設定 Instance Config

```bash
# 建立 instance 目錄
mkdir -p instances/etf_master/state

# 從範本複製
cp instance_config.json.example instances/etf_master/instance_config.json
```

編輯 `instances/etf_master/instance_config.json`：

```json
{
  "agent_id": "etf_master",
  "accounts": {
    "paper_01": {
      "alias": "paper_01",
      "broker_id": "paper",
      "account_id": "paper_default",
      "mode": "paper",
      "credentials": {}
    }
  },
  "default_account": "paper_01",
  "port": 5050,
  "watchlist": ["0050.TW", "006208.TW", "00878.TW"],
  "worldmonitor": {
    "enabled": false,
    "base_url": "https://worldmonitor-gamma-mocha.vercel.app",
    "api_key": ""
  }
}
```

> **安全提醒**：`instances/` 目錄已 gitignore，不會被 commit。切勿把憑證放入 git 追蹤的檔案。

---

## 步驟四：設定環境變數

```bash
# 建立私有 .env（已 gitignore）
cp private/.env.example private/.env
```

最少必填項目（paper 模式）：

```bash
# private/.env
AGENT_ID=etf_master
```

若要使用永豐金 live 模式，還需填入：

```bash
SINOPAC_PERSON_ID=A123456789
SINOPAC_PASSWD=your_login_password
SINOPAC_CERT_PASSWD=your_ca_cert_password
SINOPAC_CA_PATH=private/certs/Sinopac.pfx
SINOPAC_ACCOUNT=0000000
```

永豐金 CA 憑證申請：登入永豐金網站 → 智能客服 → API 申請

若要啟用 worldmonitor 全球風險雷達：

```bash
WORLDMONITOR_BASE_URL=https://worldmonitor-gamma-mocha.vercel.app
WORLDMONITOR_API_KEY=your_api_key_here
```

---

## 步驟五：設定 AGENT_ID 環境變數

ETF_TW 所有腳本都依賴 `AGENT_ID` 環境變數定位 instance 目錄：

```bash
# 加入 ~/.zshrc 或 ~/.bashrc 永久生效
export AGENT_ID=etf_master

# 或每次手動注入
AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py welcome
```

---

## 步驟六：執行環境點檢

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py check --install-deps
```

預期輸出：所有檢查項目 `✓`，無 `❌`。

---

## 步驟七：啟動 Dashboard

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

開啟瀏覽器：`http://localhost:5055`

驗證：

```bash
curl -s http://localhost:5055/api/overview | python3 -m json.tool
curl -s http://localhost:5055/health | python3 -m json.tool
```

---

## 步驟八：初始資料同步

第一次啟動需手動跑一次 refresh pipeline，建立 state 檔案：

```bash
BASE="cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3"

$BASE scripts/sync_strategy_link.py
$BASE scripts/sync_paper_state.py        # paper 模式；live 模式改用 sync_live_state.py
$BASE scripts/sync_market_cache.py
$BASE scripts/generate_market_event_context.py
$BASE scripts/generate_taiwan_market_context.py
$BASE scripts/check_major_event_trigger.py
$BASE scripts/sync_portfolio_snapshot.py
$BASE scripts/sync_ohlcv_history.py
$BASE scripts/generate_intraday_tape_context.py
$BASE scripts/sync_agent_summary.py
```

若 worldmonitor 已啟用：

```bash
$BASE scripts/sync_worldmonitor.py --mode daily
```

---

## 步驟九：設定 Cron 排程（可選）

Cron 任務已定義在 `cron/jobs.json`（7 個 job，含 worldmonitor）。

若使用 Hermes Agent 排程器：

```bash
hermes cron start
```

若不使用 Hermes，可手動加入系統 crontab：

```cron
# 早班準備（平日 08:45）
45 8 * * 1-5 cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3 scripts/sync_market_cache.py

# worldmonitor 每日快照（平日 07:50）
50 7 * * 1-5 cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3 scripts/sync_worldmonitor.py --mode daily

# worldmonitor 事件巡檢（盤中每 30 分鐘）
*/30 9-13 * * 1-5 cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python3 scripts/sync_worldmonitor.py --mode watch
```

---

## 步驟十：執行測試套件確認部署正確

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 -m pytest tests/ -q
```

預期：全部 passed，無 ERROR。

---

## 健康巡檢清單（9 項）

部署完成後或每次重大變更後，可用自動化腳本一鍵巡檢：

```bash
cd ~/.hermes/profiles/etf_master
bash scripts/verify_deployment.sh
```

或逐項手動驗證：

- [ ] `.venv/bin/python3 -c "import yfinance, pandas, numpy, shioaji, fastapi, uvicorn"` — 無 ImportError
- [ ] `curl -s http://localhost:5055/api/overview` — 回傳有效 JSON
- [ ] `curl -s http://localhost:5055/api/positions` — 回傳持倉列表
- [ ] State 檔案存在：`instances/etf_master/state/strategy_link.json`、`positions.json`、`orders_open.json`
- [ ] `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py compare 0050 00878` — 正常輸出
- [ ] Market context 可讀：`cat instances/etf_master/state/market_context_taiwan.json`
- [ ] 交易時段閘門：非交易時段嘗試下單 → 回覆「現在非交易時段，無法下單」
- [ ] Cron jobs 狀態：`cat cron/jobs.json | python3 -m json.tool` — 7 個 job 存在且 enabled
- [ ] 測試套件：`AGENT_ID=etf_master .venv/bin/python3 -m pytest tests/ -q` — 全 passed

---

## 常見問題

### Q: `ModuleNotFoundError: No module named 'shioaji'`
**A**: 用錯 Python。改用 `.venv/bin/python3`。

### Q: `AGENT_ID not set` 警告
**A**: 執行 `export AGENT_ID=etf_master` 或在指令前加 `AGENT_ID=etf_master`。

### Q: Dashboard 顯示所有欄位為空
**A**: 先跑步驟八的 refresh pipeline，建立 state 檔案。

### Q: worldmonitor 顯示「未同步」
**A**: 確認 `instance_config.json` 的 worldmonitor block 有 `"enabled": true` 且 `api_key` 正確，然後手動執行：
```bash
AGENT_ID=etf_master .venv/bin/python3 scripts/sync_worldmonitor.py --mode daily
```

### Q: Shioaji 登入失敗 `CA cert not found`
**A**: 確認 `SINOPAC_CA_PATH` 指向的 `.pfx` 檔案存在，且路徑相對於 ETF_TW 根目錄。

### Q: `api.logout()` 導致 segfault
**A**: 這是已知 Shioaji bug。**不要呼叫 `api.logout()`**，讓 process 自然退出即可。

---

## Live 交易額外步驟

> **警告**：以下步驟涉及真實資金。請先在 paper 模式完整驗證後再切換。

1. 取得永豐金 API 憑證（CA 憑證 `.pfx` 檔案）
2. 將憑證放入 `private/certs/`（已 gitignore）
3. 在 `instance_config.json` 將 `default_account` 改為 `sinopac_01`，`mode` 改為 `live`
4. 填入 `private/.env` 的永豐金憑證資訊
5. 閱讀 `references/live-trading-sop.md` 的完整 Pre-flight 檢查程序
6. 每次送單前必須通過 `validate_order.py` → `preview_order.py` → 明確確認 → `submit_order.py`

詳細流程：`skills/ETF_TW/references/live-trading-sop.md`
