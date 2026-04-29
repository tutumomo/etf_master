# 交錯修改整合審計

**日期：** 2026-04-29
**範圍：** Codex 與 Claude-code 交錯期間的 live submit / ghost order / DCA / production replay / sell scanner 修改整合。

## 審計結論

目前未發現 live submit 安全鏈路被後續修改覆蓋；`orders_open.json` 已保持空單狀態，ghost order 不再被誤判為已驗證正式委託。

Claude-code 的 production replay 揭露並修復了真實的 sell scanner mixed lot 問題：超過 1000 股且非整千股的部位，現在會拆成 board lot 與 odd lot 兩筆訊號，不再被 pre-flight gate 以 odd lot 超量攔截。

本次審計另發現 production replay 本身有一個 replay-only 缺陷：每日重寫 mock state 時清空 `position_cooldown.json`，導致 sell cooldown 沒有跨日保留。已修正為只在檔案不存在時初始化 cooldown，並重跑 replay 與更新報告。

## 已確認安全點

- `dashboard.app` 的 live submit 判斷不再用字串包含方式把 `UNVERIFIED` 誤判為 `VERIFIED`。
- dashboard live submit 與 Phase 2 ack submit 都走 `scripts/live_submit_sop.py`。
- 未驗證 live submit 會進 ghost log，不會落到 `orders_open.json`。
- `orders_open.json` 目前無 open order；dashboard health 也未回報 open order symbols。
- sell scanner mixed lot 拆單已補測試，確認 15,763 股會拆為 15,000 股 board 與 763 股 odd。

## 發現與處置

### P1：production replay 每日清空 cooldown

**狀態：已修正。**

`scripts/backtest/production_replay.py` 原本每天寫入新的 mock state 時會把 `position_cooldown.json` 重設為 `{}`，使 replay 不符合真實 ack_handler 的 sell cooldown 副作用。修正後，replay 只在 cooldown 檔不存在時初始化。

### P2：production replay 報告敘述過度樂觀

**狀態：已修正。**

舊報告寫「三情境 production 都優於或接近 BAH」，但結構化結果顯示 2024 Bull 與 2020 COVID 的 total return 明顯低於 BAH。已改為「回撤控制優於 BAH，但多頭絕對報酬偏低」。

### P2：sell split 後的 UX 可讀性仍可加強

**狀態：後續優化，不阻斷。**

mixed lot sell 會產生 board/odd 兩筆 pending signals。交易安全上是正確的，但 dashboard 後續可把同一 split group 顯示為一組出場計畫，避免使用者誤以為 AI 重複下單。

### P2：live SOP submit log 覆蓋面可再補強

**狀態：後續優化，不阻斷。**

live submit 已走 SOP 並具備 ghost order 防護；後續可補一個統一 submission journal，讓 dashboard、CLI、Phase 2 ack 的正式送單紀錄都落到同一份 audit trail。

## Replay 校正後結果

| 情境 | Production | Simulator | BAH | Gap |
|---|---:|---:|---:|---:|
| 2024 Bull | +6.50% | +27.31% | +45.32% | -20.81% |
| 2022 Bear | -5.86% | -8.09% | -24.65% | +2.23% |
| 2020 COVID | -3.05% | +0.89% | +23.69% | -3.94% |

解讀：production 的防守性更強，但 2024 多頭追漲能力不足，應列為策略 fine-tune，而不是接線阻斷 bug。

## 待收斂項目

- `skills/ETF_TW/tests/test_sell_scanner.py` 新增 mixed lot regression test，需在下一次收工時納入 commit。
- `graphify-out/` 已因前次 wiki / code rebuild 變動，需在下一次收工時確認同步。
- 工作區仍存在多個非 ETF_TW code 的既有 dirty files，未在本次審計中整理，避免誤動使用者或工具狀態。
