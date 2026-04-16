# Layered Review Scheduling

## 目的

將 AI 建議後的自動復盤，從單一隔日檢查提升為分層復盤機制：
- T+1 早期復盤
- T+3 短期復盤
- T+10 中期復盤

---

## 原則

1. T+1 不是最終裁判，只是早期檢查點
2. T+3 / T+10 才逐步形成更穩定的 outcome interpretation
3. 每一筆 AI 建議應能綁定自己的 layered review schedule plan
4. schedule plan 應能被未來 cron / task runner 直接消費

---

## 最小結構

每筆建議建立一份 schedule plan：
- `request_id`
- `windows`
- `binding.runner`
- `binding.state_artifact`
- `binding.schedule_kind`

---

## 目前 Runner

- `scripts/auto_post_review_cycle.py`

目前先作為統一 runner，之後可依 window type 再分化更細的策略。

---

## 下一步

1. 將 schedule plan 寫入 state / ledger
2. 決定是否由 cron 產生對應排程任務
3. 讓不同 window 產生不同層級的 outcome / reflection 內容
