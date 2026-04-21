# Design: Learned Rules Evolution（決策閉環學習）

Date: 2026-04-22

## 背景與動機

受 Karpathy autoresearch 啟發：「改 → 跑 → 量 → 保留或丟棄 → 再改」的閉環。

etf_master 現有的 T1/T3/T10 復盤已完成「跑」和「量」，`auto_calibrate_thresholds` 完成了數值門檻的閉環，但 `ai_auto_reflection.py` 產出的反思文字從未回饋到 AI Bridge 的輸入源——AI 下次決策時看不到上週教訓。

本設計補上這個缺口：讓週報統計 → LLM 歸納規則 → 寫入 `wiki/learned-rules.md` → AI Bridge 第 16 個輸入源，形成完整的 autoresearch 閉環。

---

## 架構：資料流與觸發時機

```
週六 09:05 cron
  └─ generate_decision_quality_weekly.py
       ├─ 1. 產出週報 markdown（已有）
       ├─ 2. auto_calibrate_thresholds（已有）
       └─ 3. [新] _generate_learned_rules_via_bridge()
              │
              ├─ 讀 decision_quality_report.json (chain_breakdown)
              ├─ 讀 decision_provenance.jsonl (本週 top_wins/losses)
              ├─ 讀 state/learned_rules_meta.json (現有規則庫)
              │
              ├─ 組統計摘要 prompt
              │   → 注入 ai_decision_request.json
              │       wiki_context.learned_rules_draft
              │
              ├─ 呼叫 generate_ai_agent_response.py（已有）
              │
              ├─ 從 ai_decision_response.json 取出
              │   reasoning.learned_rules (JSON array)
              │
              └─ 執行滾動邏輯
                  → 寫 wiki/learned-rules.md
                  → 更新 state/learned_rules_meta.json

generate_ai_decision_request.py（現有，小改）
  └─ 第 16 個輸入源：讀 wiki/learned-rules.md
       → wiki_context.learned_rules
       （不存在或 stale → 空字串，不阻斷）
```

---

## learned-rules.md 格式（版本化滾動）

```markdown
## 學習規則庫
generated_at: 2026-04-22T09:05:00+08:00

### RULE-001
- **規則**：高波動情境下 rule_engine 勝率低於 40% 時，建議延後買入
- **來源統計**：rule_engine win_rate=32%, 樣本=14, 情境=elevated
- **出現次數**：3
- **首次出現**：2026-W15
- **最後確認**：2026-W17
- **狀態**：active（連續 2 週確認）
```

### 滾動規則

| 狀態 | 條件 | 行為 |
|------|------|------|
| `tentative` | 首次出現 | 保留，等下週確認 |
| `active` | 連續 ≥2 週出現 | prompt 中標記高權重 |
| `stale` | 超過 4 週未出現 | 標記待淘汰 |

**上限 15 條**：超過時淘汰最舊的 `stale` 規則。若無 stale 可淘汰，保留前 15 條（按出現次數降序）。

### 狀態機

```
首次出現 → tentative
連續第 2 週出現 → active
active/tentative 且 4 週未出現 → stale
stale 且規則數 > 15 → 刪除
```

---

## 統計摘要 Prompt 結構

注入 `wiki_context.learned_rules_draft`：

```
你是 ETF_Master 的決策品質分析師。
根據以下本週復盤統計，歸納出 1–5 條具體可執行的投資決策規則。

【本週統計】
- rule_engine: 總計 N 筆, 勝率 X%, 敗率 Y%
- ai_bridge: 總計 N 筆, 勝率 X%, 敗率 Y%
- tier1_consensus: 總計 N 筆, 勝率 X%
- 本週最準確: [symbol / window / return%]
- 本週最大失誤: [symbol / window / return%]

【現有規則庫摘要（避免重複）】
RULE-001: xxx（出現3次，active）
...

【輸出格式】（JSON array，純 JSON，無其他文字）
[
  {
    "rule_text": "...",
    "source_stats": "...",
    "is_existing_rule_id": null  // 強化既有規則時填入 "RULE-001"
  }
]
```

AI 輸出從 `ai_decision_response.json` 的 `reasoning.learned_rules` 取出。

---

## 新增檔案

| 檔案 | 用途 |
|------|------|
| `scripts/generate_learned_rules.py` | 核心邏輯：組 prompt、解析輸出、執行滾動、寫 wiki |
| `state/learned_rules_meta.json` | 規則庫 metadata（出現次數、首次/最後確認週、狀態） |
| `wiki/learned-rules.md` | AI Bridge 第 16 個輸入源 |
| `tests/test_generate_learned_rules.py` | 單元測試 |

### 現有檔案改動

| 檔案 | 改動 |
|------|------|
| `scripts/generate_decision_quality_weekly.py` | 週報末尾呼叫 `generate_learned_rules.run()` |
| `scripts/generate_ai_decision_request.py` | 加入第 16 個輸入源：讀 `wiki/learned-rules.md` → `wiki_context.learned_rules` |
| `scripts/generate_ai_agent_response.py` | `reasoning` dict 加入 `learned_rules` 欄位輸出 |

---

## 錯誤處理

| 失敗點 | 處理方式 |
|--------|---------|
| `ai_decision_response.json` 無 `learned_rules` 欄位 | 跳過本週更新，保留上週 md 不動 |
| LLM 輸出非合法 JSON array | log warning，跳過，不覆寫 |
| `wiki/learned-rules.md` 寫入失敗 | try/except + warning，週報仍標記成功 |
| `generate_ai_decision_request.py` 讀不到 md | 回傳空字串，不阻斷決策掃描 |
| 樣本數不足（total < 5） | 跳過 LLM 呼叫，本週不更新規則 |

---

## 測試策略

`tests/test_generate_learned_rules.py`：

| 測試案例 | 驗證重點 |
|---------|---------|
| 統計摘要組裝 | 給定 chain_breakdown → prompt 包含正確數字 |
| 滾動：新規則首次出現 | 狀態 `tentative`，出現次數=1 |
| 滾動：連續 2 週出現 | 狀態升為 `active` |
| 滾動：4 週未出現 | 狀態變 `stale` |
| 上限 15 條：第 16 條進來 | 最舊 stale 規則被移除 |
| LLM 輸出非法 JSON | 不覆寫既有 md |
| `learned-rules.md` 不存在 | `generate_ai_decision_request` 回傳空字串不報錯 |
| 強化既有規則（is_existing_rule_id） | 出現次數+1，last_confirmed 更新 |
| 樣本不足（total < 5） | 不呼叫 LLM，md 不變 |

---

## 成功指標

- 每週六 09:05 後 `wiki/learned-rules.md` 有新內容
- `generate_ai_decision_request.py` 的 `wiki_context.learned_rules` 非空
- 連續 3 週後至少 1 條規則狀態為 `active`
- 任何環節失敗不影響週報主流程完成
