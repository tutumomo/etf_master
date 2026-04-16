# ETF_TW Dashboard Runbook

## Dashboard Change SOP（強制）
只要有改動會影響 Dashboard（包含 `dashboard/`、`dashboard/templates/`，或 Dashboard 讀取的 state contract / scripts），必須遵循以下固定流程：

1) 先交付可審核的變更清單
- 變更檔案路徑清單
- 重點差異（使用者可理解的版本）
- commit id
- 變更後在頁面上會出現的位置（哪張卡/哪段）

2) 重啟 Dashboard
- 若已存在舊的 uvicorn/python 進程在同 port 監聽，必須先 stop/kill，避免舊 code 繼續服務造成 template/context mismatch。
- 然後依 BOOT.md 標準路徑啟動：

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
```

3) 自我驗證（改完必做）
至少確認：
- `/health` → 200
- `/` → 200（模板可正常 render）
- `/api/overview` → 200

## State Source Rule
Dashboard 正式讀取來源為：

```text
ETF_TW/instances/<agent_id>/state/
```

而不是 root `ETF_TW/state/`，也不是任何歷史副本的殘留 state。

## Symbol Normalization Rule
Dashboard 顯示層預期收到的是 canonical symbol：`0050`、`00878`、`006208`、`00679B`。
不應在 watchlist / tape / summary 中同時看到 `0050` 與 `0050.TW` 這種重複 key。

## Agent Summary 同步

Dashboard 依賴 `sync_agent_summary.py` 定期將持倉摘要、KPI 與風險訊號寫入 `instances/<agent_id>/state/agent_summary.json`。若此檔案過期或缺失，overview 頁面的持倉卡片將顯示空白。
