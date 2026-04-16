---
name: etf-tw-hermes-migration-cleanup
description: 清理 ETF_TW 從 OpenClaw 遷移到 Hermes 後殘留的文件/路徑/維運遺毒；先分辨 active 副本，再先修文件、後修程式。
---

# ETF_TW Hermes Migration Cleanup

## 何時使用
- 使用者說 Hermes 版 ETF_TW 與 OpenClaw 版混在一起
- GitHub 拉下來是舊版，但本機跑的 dashboard 又是另一份
- 文件還在教人用 `~/.openclaw/skills/ETF_TW`
- dashboard / scripts / tests 仍綁 `.openclaw` 路徑

## 核心原則
1. 先搞清楚 active 副本，再動手
2. 先清文件層誤導，再清程式層耦合
3. 每個里程碑先保住（branch/tag/commit），避免再次蒸發
4. 不要一邊修 Hermes，一邊又拿 OpenClaw 路徑當真

## Step 1：先辨識哪份 ETF_TW 在跑
至少對照：
- Hermes：`~/.hermes/profiles/<profile>/skills/ETF_TW`
- OpenClaw：`~/.openclaw/skills/ETF_TW`
- dashboard 實際啟動指令 / port / repo git 狀態

如果使用者說「GitHub 拉下來是舊版」，要警覺：
- 可能昨天改的是 OpenClaw 副本
- 今天 pull 到 Hermes 的是另一份
- 兩邊都不等於使用者記得的 OK 版

## Step 2：先做文件層清毒（第一批，最優先）
優先檔案：
- `BOOT.md`
- `README.md`
- `INSTALL.md`
- `dashboard/README.md`
- `IDENTITY.md`
- `SKILL.md`
- `references/roadmap.md`

### 典型要改的內容
- `~/.openclaw/skills/ETF_TW` → `~/.hermes/profiles/etf_master/skills/ETF_TW`
- `localhost:5050` → `localhost:5055`
- `OpenClaw Agent` → `Hermes Agent`
- `請透過 OpenClaw agent 反饋` → `請透過 Hermes Agent 反饋`
- 若要保留歷史教訓，改成「舊系統遷移期踩雷」而不是把 OpenClaw 當現行主體

### 文件層驗證
搜尋這批檔案中是否還有：
- `.openclaw`
- `OpenClaw`
- `localhost:5050`
- `openclaw cron`

如果這批文件搜不到上述關鍵字，代表第一批清毒完成。

## Step 3：再做程式層清毒（第二批）
高風險檔案：
- `dashboard/app.py`
- `scripts/sync_strategy_link.py`
- `scripts/sync_agent_evolution.py`
- `scripts/sync_portfolio_snapshot.py`
- `scripts/verify_alignment.py`
- `scripts/etf_core/context.py`
- cron registry 相關腳本
- tests 中所有硬編碼 `.openclaw` 路徑

### 典型遺毒
- `Path.home() / ".openclaw" / ...`
- 寫死 `/Users/.../.openclaw/...`
- `openclaw cron list/add`
- 測試 import `.openclaw/skills/ETF_TW/...`
- `strategy_state.json` / `memory/` 仍從 `.openclaw/agents/...` 取

### 已驗證的安全改法（這輪實戰）
1. `dashboard/app.py`
   - `ETF_MASTER_STRATEGY_PATH` 不要再指 `.openclaw/agents/...`
   - 改成 `context.get_instance_dir() / "strategy_state.json"`
   - `write_strategy_state()` 若檔案不存在，直接建立 fallback payload，避免 Hermes 首次啟動就炸掉
2. `scripts/sync_strategy_link.py`
   - 直接改用 `context.get_instance_dir() / "strategy_state.json"`
   - 若不存在，自動建立預設：`核心累積 / 無`
3. `scripts/sync_portfolio_snapshot.py`
   - `MEMORY_PATH` 改成 `context.get_instance_dir() / "memory"`
   - 不要再往 `.openclaw/agents/.../memory` 回讀
4. `scripts/sync_agent_evolution.py`
   - 若本質上是 OpenClaw 家族 agent 複製器，Hermes 版先降級成 no-op / warning placeholder
   - 比硬搬舊邏輯安全，避免跨 instance 污染

### 程式層驗證
至少要做：
```bash
.venv/bin/python -m py_compile \
  dashboard/app.py \
  scripts/sync_strategy_link.py \
  scripts/sync_agent_evolution.py \
  scripts/sync_portfolio_snapshot.py
```

再搜尋這批檔案是否還有：
- `.openclaw`
- `OpenClaw`

如果這批檔案兩個關鍵字都搜不到，代表第二批主幹清毒完成。

### 這輪新增的驗證補充
- 針對 cron / account / dashboard 啟動鏈，再加跑：
```bash
.venv/bin/python -m py_compile \
  scripts/account_manager.py \
  scripts/adapters/sinopac_adapter.py \
  scripts/sync_agent_evolution.py \
  scripts/layered_review_cron_registry.py \
  scripts/layered_review_cron_registry_live.py \
  scripts/register_layered_review_jobs.py \
  scripts/register_layered_review_jobs_via_tool.py \
  scripts/register_standard_cron_pack.py
```
- 最後對整個 ETF_TW 根目錄做一次 content search：
  - `openclaw`
  - `OpenClaw`
  - `.openclaw`
  - `openclaw.json`
- 目標不是只減少命中，而是做到 Hermes-only 清理後 0 命中

### 這輪新增的實戰補充（Hermes-safe 第二批）
5. `scripts/verify_alignment.py`
   - `AGENT_STRATEGY` 改成 `context.get_instance_dir() / "strategy_state.json"`
   - 不要再去 `.openclaw/agents/...`
6. `scripts/etf_core/context.py`
   - `get_port()` Hermes 預設改為 `5055`，不要留 `5050`
   - `OPENCLAW_AGENT_NAME` 可保留為 legacy 相容，但說明文字必須明確標成 migration compatibility，而不是現行主路徑
7. `scripts/setup_agent.py`
   - 若原本整支都是 OpenClaw agent provisioning 邏輯，Hermes 版可直接重寫成「只初始化 `instances/<agent_id>/...`」的簡化工具
   - 不要再建立 / 依賴 `.openclaw/agents/...`
8. `scripts/venv_executor.py`
   - 文件與變數說明改成：優先 `AGENT_ID`，兼容 legacy `OPENCLAW_AGENT_NAME`
9. `scripts/run_etf_tw_task.py`
   - 從 `state_dir` 推導 instance 時，先設 `AGENT_ID`，可同步補 legacy env 以兼容舊腳本
10. `dashboard/app.py` 啟動預設 env
   - 若沒有 instance env，先設 `AGENT_ID=etf_master`
   - 不要優先硬塞 `OPENCLAW_AGENT_NAME`
11. `scripts/start_dashboard.sh`
   - 根目錄必須改成 `~/.hermes/profiles/etf_master/skills/ETF_TW`
   - port 必須對齊 `5055`，不要留 `8765`
   - 既有進程判斷必須匹配 Hermes 根路徑，不能再用 `.openclaw/skills/ETF_TW`
   - 驗證不要用 Python `py_compile` 去檢查 `.sh`；要額外跑 `zsh -n scripts/start_dashboard.sh`
12. `scripts/dashboard_guard.py`
   - fallback / default port 也要一起改成 `5055`，否則 guard 會把舊 5050 視為正確目標
13. `scripts/account_manager.py`
   - `_find_config()` 不要再 fallback 到 `.openclaw/agents/<id>/instance_config.json`
   - Hermes 版應只認 instance config 與 Hermes 技能樹內的 config
13. legacy cron bridge 腳本
   - `scripts/layered_review_cron_registry.py`
   - `scripts/layered_review_cron_registry_live.py`
   - `scripts/register_layered_review_jobs.py`
   - `scripts/register_layered_review_jobs_via_tool.py`
   - `scripts/register_standard_cron_pack.py`
   - 在 Hermes 模式下，不要再假裝可用 `openclaw cron ...` 落地
   - 安全作法是：改成 Hermes 語義（`cronjob` tool / `hermes cron create`），或至少明確回傳 disabled / error，避免使用者誤以為已註冊成功
14. plugin 殘留
   - 若技能根目錄還有 `openclaw.plugin.json`，Hermes-only 清理時直接刪除
15. 全樹驗證標準
   - 清理完成後，不只看單一腳本；直接對整個 ETF_TW 根目錄做 search
   - 目標是 `openclaw` / `OpenClaw` / `.openclaw` / `openclaw cron` / `openclaw.json` 都 0 命中
   - 若只剩 placeholder 測試資料（例如假帳號、假 API key）但不涉及舊系統語義，可列為非阻斷項
16. 文案層清毒
   - `BOOT.md` / `README.md` / `INSTALL.md` / `dashboard/README.md` / `SKILL.md` / `OPTIMIZATION_LOG.md`
   - 若只是要保留歷史事故，改成「舊系統 / 歷史副本 / 舊版 cron 鏈」等中性描述
   - 不要再把 OpenClaw 寫成現行可操作環境

## Step 3.5：測試檔批次清毒（第三批）
Hermes 遷移時，`tests/` 常會大量硬編碼：
- `/Users/.../.openclaw/skills/ETF_TW/...`
- `sys.path.insert(0, "/Users/.../.openclaw/skills/ETF_TW/scripts")`

### 實戰可行做法
- 先批量搜尋 `tests/test_*.py`
- 以腳本一次性替換 `.openclaw/skills/ETF_TW` → Hermes 實際 skill root
- 之後再跑一次搜尋確認 `tests/` 內已 0 命中
- 再用 `py_compile` 批量驗證所有 test 檔語法

### 注意
- 這一步主要是先解除錯路徑依賴，不一定代表 tests 已經全部語意正確
- 但若不先清路徑，Hermes 版測試永遠在打錯副本

## Step 4：里程碑管理
每完成一批就：
1. `git status`
2. 檢查改動範圍
3. commit
4. push
5. 回報 commit hash

不要只說「已改好」，一定要明示 hash。

## 常見坑
- 使用者說的是 ETF_TW 技能本體，不是 Hermes 主 repo
- 文件清乾淨了，不代表程式沒問題；但文件層一定要先清，不然會持續誤導維運
- GitHub 上的是舊版，不代表本機 active 版本是同一份
- 有 commit / push，不代表 push 的內容就是使用者驗收過的版本；一定要核對 commit 內容

## 交付物
- 一份「active 副本判定」結論
- 一次文件層清毒 commit
- 一次程式層清毒 commit
- 明確列出仍未清的 OpenClaw 耦合點
