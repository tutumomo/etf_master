# AI Research Method for ETF_TW

## 目的

將 `karpathy/autoresearch` 對智能體自我研究 / 自我迭代的核心方法論，轉譯為 ETF_TW 可用的決策進化框架。

重點不是照抄其模型訓練流程，而是吸收其：
- 固定可比較實驗單位
- 固定 quality metric
- policy-driven 迭代
- 小步可回滾
- 自動研究與執行授權分離

---

## 核心原則

### 1. 固定可比較迭代
每次智能體進化，都應可回答：
- 改了什麼
- 想改善什麼
- 後續 quality / outcome 是否真的變好

### 2. 固定 quality metric
智能體進化不能只看主觀感覺，需有穩定 quality 指標，例如：
- reviewed_rate
- superseded_rate
- early_review_quality
- short_review_quality
- mid_review_quality
- confidence_calibration_hint

### 3. Policy-driven 進化
進化不只藏在 Python if/else，而應逐步形成：
- decision policy
- confidence calibration policy
- review interpretation policy

### 4. 小步可回滾
每次只改一小塊 decision / review / reflection 邏輯，方便比較與回退。

### 5. 自動研究、自動復盤，但執行授權分離
AI 可以自動：
- 給出建議
- 留存紀錄
- 自動復盤
- 自動反思
- 更新 quality state

但是否下單，仍由 owner 透過對話授權。

---

## 套用到 ETF_TW 的具體設計

### Decision Layer
- `ai_decision_request.json`
- `ai_decision_response.json`

### Review / Outcome / Reflection Layer
- `ai_decision_review.jsonl`
- `ai_decision_outcome.jsonl`
- `ai_decision_reflection.jsonl`

### Memory / Quality Layer
- `decision_memory_context`
- `quality_hooks`
- `ai_decision_quality.json`

### Layered Review Layer
- T+1 early review
- T+3 short review
- T+10 mid review
- `layered_review_plan.json`

---

## 下一步建議

1. 在 `ai_decision_quality.json` 逐步加入更穩定的 quality metrics
2. 讓 agent response 優先讀取正式 quality state，而不只讀 request 內嵌 hooks
3. 讓 layered review 透過 scheduler / cron 轉為真正自動執行
4. 將 reflection 提升為 pattern summary，而不只單筆 note

---

## 一句話總結

ETF_TW 應將 AI 進化流程設計成：

> 可比較、可留痕、可度量、可回滾、可回灌的研究流程。

這才是將 autoresearch 的精華真正納入 ETF_TW 的方式。
