# Layered Review Cron Standard

## 目的
定義 ETF_TW layered review 自動排程的標準註冊格式，避免不同 agent / instance 各自建立不一致 job。

## 標準流程
1. 先產生 `layered_review_plan.json`
2. 再產生 `layered_review_registrations.json`
3. 再轉成 cron-ready jobs
4. 註冊前先做 dedupe：
   - 本地 registry：`layered_review_cron_jobs.json`
   - live cron list / 實際排程回應
5. 只有未存在的 dedupe key 才可 add

## dedupe_key
`<request_id>::<review_window>`

## sessionTarget
預設：`isolated`

## runner
標準 runner：`scripts/auto_post_review_cycle.py`

## 已驗證原則
- request-driven layered review 必須附帶 `request_id` / `review_window`
- dedupe 必須以 live list 或實際排程查詢為主，不能只信本地 registry
- runner 只做復盤 / outcome / reflection，不會下單

## 標準入口
- `scripts/register_layered_review_jobs.py`
