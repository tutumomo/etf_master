# ETF_TW Production Replay 驗證報告（B 計畫）

**日期：** 2026-04-29
**目標：** 驗證生產代碼 (`buy_scanner` + `sell_scanner` + `peak_tracker` + `initial_dca`) 在歷史資料上的行為是否與 simulator 一致。

**初始資金：** 1,000,000 TWD　**DCA：** 啟用 60% / 20 日　**標的：** 0050.TW

## 結果對照

| 情境 | Production | Simulator | BAH | Gap (Rep − Sim) |
|---|---|---|---|---|
| **2024 Bull** | +6.50% (DD -4.65%) | +27.31% (DD -5.31%) | +45.32% | -20.81% |
| **2022 Bear** | -5.86% (DD -6.52%) | -8.09% (DD -9.42%) | -24.65% | +2.23% |
| **2020 COVID** | -3.05% (DD -4.86%) | +0.89% (DD -5.72%) | +23.69% | -3.94% |

### 交易次數對照

| 情境 | Production buy/sell | Simulator buy/sell |
|---|---|---|
| 2024 Bull | 54 / **6** | 57 / 2 |
| 2022 Bear | 79 / **9** | 86 / 4 |
| 2020 COVID | 56 / **6** | 61 / 2 |

**DCA buy 一致**（三情境皆 20/20），但 total buy 少於 simulator，主因是 production replay 現在保留 sell cooldown，trailing 出場後會阻擋 cooldown 期間重新買回。
**sell 多於 simulator** — production 的 board/odd 拆單與 cooldown 後補買，使同一段行情可能產生多筆 sell。

---

## 揭露的兩個生產 bug（已修復）

### Bug 1：odd lot blocking
**症狀：** sell_scanner 試圖把整批部位（如 15,763 股）標 lot_type='odd' 送 pre_flight_gate，gate 規定 odd lot 只能 1-999 股 → 永遠被擋下，無法賣出。

**修復：** `sell_scanner.run_sell_scan` 把超過 1000 股但非整千倍的部位**拆成兩筆訊號**：
- 整張部分（lot_type='board'）
- 零股部分（lot_type='odd'，1-999 股）

兩筆都過 gate，分別 enqueue（trigger_payload 帶 split_part 標籤）。

### Bug 2：cooldown 每日被 replay 清空（replay-only）
**症狀：** replay 的 `write_daily_state` 每日把 `position_cooldown.json` 重寫成 `{}`，導致前一日 sell ack 寫入的 cooldown 在下一日 buy_scan 前消失。

**修復：** replay 只在 cooldown 檔不存在時初始化，之後保留 `write_sell_cooldown` 的副作用。這使 replay 更接近生產行為，也讓 buy 次數從原本完全貼齊 simulator，調整為反映 cooldown 後的實際差異。

---

## Production vs Simulator 差距的非 bug 解釋

差距主因是兩者「**部位概念**」不同：
- **Simulator**：單一 position，trailing 觸發 → 全部 sell → reset peak_close → 重來
- **Production**：每次 buy 累積到同一個 position，trailing 觸發 → 可能拆成 board/odd 多筆 sell → 7 日 cooldown

這個結構在 2024 Bull 中讓 production 在 4 月就先觸發一次 trailing（賣早），錯失後續主升段；而 simulator 只在 7-18 與 8-05 賣兩次。

**這不是阻斷性 bug，是 production 設計（cooldown + 拆 lot + 重新進場規則）的副作用**。要追平 simulator 需調整出場後重新進場與 trailing grace period，但這已經是策略調優、不在 B 計畫範圍。

---

## 關鍵驗證

✅ **DCA 邏輯一致**：三情境 DCA 皆 20/20
✅ **trailing 邏輯邏輯正確**：peak_close、stop_price、is_locked_in 計算正確
✅ **macro_buy_gate 生效**：在 macro_neutral 下 haircut 50% 倉位
✅ **DCA 凍結 trailing 生效**：前 20 日 sell_scanner 把部位歸入 dca_trailing_frozen
✅ **回撤控制有效**：三情境 production 最大回撤皆優於 BAH
⚠️ **多頭絕對報酬偏低**：2024 Bull production 明顯落後 simulator 與 BAH，主要因為更早觸發 trailing 並進入 cooldown

---

## 結論

**生產代碼接通成功，沒有阻斷性 bug**。修復 odd lot 拆單後：
- 三情境的 DCA、trailing、macro gate 都能在 production replay 中被觸發與驗證
- 最大回撤都比 BAH 小（保護資金有效）
- cooldown 保留後，production replay 更接近真實 ack 後狀態

但**絕對報酬有 2-21% 的下調**，主因是 production 的部位管理機制（cooldown + 拆單）讓 trailing 觸發時更積極地清倉，在多頭時錯失後續上漲。

### 下次該調的（不在 B 範圍）

1. **整併連續 trailing 觸發**：同一 position 7 日內多次 trailing 應視為同一次出場，避免拆成 8-9 次小 sell
2. **cooldown 後重新進場機制**：cooldown 結束後若 macro 仍 bullish，可考慮自動加碼一次（取代等 ladder 觸發）
3. **DCA 完成後 grace period**：DCA 結束後 N 日內不啟動 trailing（已有部分機制，可放寬）

---

## 工件

- `scripts/backtest/production_replay.py` — replay 腳本
- `docs/intelligence-roadmap/backtest-reports/2026-04-29-production-replay.json` — 結構化結果
- `scripts/auto_trade/sell_scanner.py` — odd lot 拆單修復
