# Auto Decision Review Pipeline — Design Spec

**Date:** 2026-04-19
**Version:** v1.0
**Status:** Approved

---

## Goal

完全自動化「規則引擎 + AI Bridge 雙鏈建議 → T+N 價格回填 → win/loss/flat 判定 → 雙鏈分開統計 → 週報寫入 wiki」的整個循環，消除所有需要人工標記 `reviewed`/`superseded` 的手動步驟，讓決策數據以每日盤後頻率自動累積。

## Architecture

三個子系統依序串接，由兩個 cron job 驅動：

```
每天 15:05（盤後）
  └── sync_decision_reviews.py
        ├── 掃描 decision_provenance.jsonl 中到期的 T1/T3/T10 窗口
        ├── 拉收盤價（market_cache → yfinance fallback）
        ├── 計算 return_pct，判定 verdict
        ├── 回寫 provenance T1/T3/T10
        ├── 當三個窗口都填滿 → 寫 outcome_final
        └── 更新 decision_quality_report.json（雙鏈統計）

每週六 09:05
  └── generate_decision_quality_weekly.py
        ├── 讀取 decision_provenance.jsonl
        ├── 計算本週 + 累計雙鏈勝率
        └── 寫 wiki/decision-weekly-YYYY-WNN.md
```

## Sub-System 1: 自動 T+N 回填與判定

### 腳本
`scripts/sync_decision_reviews.py`

### 觸發方式
新增到 `cron/jobs.json`：`ETF 盤後收工` cron（15:00）完成後，於 15:05 執行。

### T+N 到期計算
| 窗口 | 到期條件 | 說明 |
|------|---------|------|
| T1 | `created_at` 距今 ≥ 1 個交易日 | 最快隔天盤後即可填 |
| T3 | `created_at` 距今 ≥ 3 個交易日 | |
| T10 | `created_at` 距今 ≥ 10 個交易日 | |

交易日計算：排除週六、週日（不考慮台灣國定假日，後續可配置）。

### 收盤價取得順序
1. `market_cache.json` 的 `quotes[symbol].current_price`，若 `updated_at` 距今 ≤ 6 小時則使用
2. Fallback：`yfinance` 拉最近一個交易日收盤價（`history(period="5d")[-1]`）
3. 若兩者皆無 → `verdict = "skip"`，留 null，下次繼續嘗試

### Verdict 判定門檻（可配置）
```python
WIN_THRESHOLD  = +0.015   # +1.5%
LOSS_THRESHOLD = -0.015   # -1.5%
```
- `return_pct >= WIN_THRESHOLD`  → `"win"`
- `return_pct <= LOSS_THRESHOLD` → `"loss"`
- 其餘                           → `"flat"`

### T+N 欄位格式
```json
{
  "reviewed_at": "2026-04-20T15:05:12+08:00",
  "price_then": 173.50,
  "reference_price": 171.20,
  "return_pct": 1.34,
  "verdict": "flat",
  "source": "market_cache"
}
```

### outcome_final 判定
當三個窗口（T1/T3/T10）全部填入非 null 值後，自動計算：
```json
{
  "finalized_at": "...",
  "verdict": "win",           // 三窗口中勝率最多的 verdict
  "max_return_pct": 2.10,     // 三窗口中最高報酬率
  "min_return_pct": 0.50,
  "t1_verdict": "flat",
  "t3_verdict": "win",
  "t10_verdict": "win"
}
```

## Sub-System 2: 雙鏈分開統計

### provenance 補充欄位（`chain_sources`）

在 `run_auto_decision_scan.py` 的 `build_provenance_record()` 呼叫處，將 `scan_result` 中已有的 `consensus` dict 傳入，在 provenance record 新增：

```json
"chain_sources": {
  "rule_engine_action": "buy-preview",
  "rule_engine_symbol": "00878",
  "ai_bridge_action": "preview_buy",
  "ai_bridge_symbol": "00878",
  "consensus_tier": 1,
  "consensus_resolved": "buy",
  "strategy_aligned_rule": true,
  "strategy_aligned_ai": true
}
```

既有 26 筆 provenance 因缺少此欄位，統計時視為 `chain_sources = null`，計入「來源未知」桶，不排除。

### decision_quality_report.json 擴充欄位

現有 `decision_quality_report.json` 新增 `chain_breakdown` 區塊：

```json
{
  "chain_breakdown": {
    "rule_engine": {
      "total": 18,
      "win": 8, "loss": 4, "flat": 5, "skip": 1,
      "win_rate": 0.444
    },
    "ai_bridge": {
      "total": 18,
      "win": 10, "loss": 3, "flat": 4, "skip": 1,
      "win_rate": 0.556
    },
    "tier1_consensus": {
      "total": 12,
      "win": 7, "loss": 2, "flat": 3,
      "win_rate": 0.583
    },
    "unknown_source": {
      "total": 8,
      "win": 3, "loss": 2, "flat": 3,
      "win_rate": 0.375
    }
  },
  "last_updated": "2026-04-20T15:05:30+08:00",
  "total_decisions_with_outcome": 26,
  "total_pending": 0
}
```

只統計 `outcome_final != null` 的記錄（T1/T3/T10 全部填滿才算一筆完整樣本）。

## Sub-System 3: 週報自動寫入 Wiki

### 腳本
`scripts/generate_decision_quality_weekly.py`

### 觸發方式
新增到 `cron/jobs.json`：週六 09:05（緊接 `ETF 每週深度復盤` 09:00 之後）。

### 輸出路徑
`wiki/decision-weekly-YYYY-WNN.md`（例：`wiki/decision-weekly-2026-W17.md`）

同時更新 `wiki/decision-quality-latest.md`（固定路徑，供 `generate_ai_decision_request.py` 引用）。

### 週報格式
```markdown
---
title: ETF 決策品質週報 2026-W17
date: 2026-04-26
period: 2026-04-20 ~ 2026-04-26
---

## 本週摘要
- 新增決策建議：N 筆
- 完成 T1 回填：N 筆 / T3：N 筆 / T10：N 筆
- 本週到期完整樣本：N 筆

## 雙鏈勝率（累計）
| 鏈路 | 樣本數 | 勝率 | 敗率 | 平盤率 |
|------|--------|------|------|--------|
| 規則引擎 | 18 | 44.4% | 22.2% | 33.3% |
| AI Bridge | 18 | 55.6% | 16.7% | 22.2% |
| Tier 1 共識 | 12 | 58.3% | 16.7% | 25.0% |

## 本週最準確標的（Top 3）
1. 00878 — T3 win (+2.1%)
2. 0050 — T1 win (+1.8%)
3. 006208 — T10 win (+3.2%)

## 本週最大失誤（Top 3）
1. 00679B — T3 loss (-2.3%)
2. 00919 — T1 loss (-1.7%)

## 決策品質趨勢（最近 4 週）
| 週次 | 樣本 | AI勝率 | 規則勝率 | Tier1勝率 |
|------|------|--------|---------|-----------|
| W14 | 8 | 50% | 37.5% | 55.6% |
| W15 | 11 | 54.5% | 45.5% | 60% |
| W16 | 9 | 44.4% | 33.3% | 50% |
| W17 | 12 | 58.3% | 41.7% | 66.7% |
```

### wiki_context 自動引用
`generate_ai_decision_request.py` 已有 wiki 路徑自動解析邏輯，只要 `wiki/decision-quality-latest.md` 存在，AI Bridge 即可在每次決策時引用歷史勝率作為輸入之一。

## Cron 異動

| Job 名稱 | 排程 | 異動 |
|----------|------|------|
| ETF 盤後收工 | 15:00 平日 | **不變**（保持現有） |
| **ETF 決策自動復盤** | **15:05 平日** | **新增** |
| ETF 每週深度復盤 | 09:00 週六 | **不變** |
| **ETF 決策品質週報** | **09:05 週六** | **新增** |

## 新增/修改檔案清單

| 檔案 | 類型 | 說明 |
|------|------|------|
| `scripts/sync_decision_reviews.py` | 新增 | T+N 自動回填主腳本 |
| `scripts/generate_decision_quality_weekly.py` | 新增 | 週報產出腳本 |
| `scripts/provenance_logger.py` | 修改 | `build_provenance_record()` 接受 `chain_sources` 參數 |
| `scripts/run_auto_decision_scan.py` | 修改 | 傳入 `consensus` dict 到 `build_provenance_record()` |
| `instances/<agent_id>/state/decision_quality_report.json` | 修改 | 新增 `chain_breakdown` 欄位 |
| `cron/jobs.json` | 修改 | 新增兩個 cron job |
| `wiki/decision-quality-latest.md` | 新增（執行後） | 週報固定路徑 |
| `tests/test_sync_decision_reviews.py` | 新增 | 回填邏輯單元測試 |
| `tests/test_generate_decision_quality_weekly.py` | 新增 | 週報格式測試 |

## 不在本次範圍內

- 台灣國定假日日曆（T+N 用簡化的「排除週末」算法）
- Dashboard 新增復盤卡片（可作為後續 phase）
- 歷史 26 筆 provenance 的 backfill（yfinance 可拉歷史收盤，但 T+N 到期日已過，留作選填功能）
- live 下單成交後的真實 PnL 追蹤（本次只追蹤「建議的理論報酬率」）

## 成功驗收條件

1. `sync_decision_reviews.py` 執行後，所有到期的 T+N 欄位自動填滿（非 null）
2. 不需要任何人工標記 `reviewed`/`superseded` 即可觸發 verdict 判定
3. `decision_quality_report.json` 的 `chain_breakdown` 有 `rule_engine`/`ai_bridge`/`tier1_consensus` 三個桶的勝率
4. 週六 `wiki/decision-quality-latest.md` 自動更新，內容包含雙鏈勝率表格
5. `generate_ai_decision_request.py` 的 `wiki_context` 能讀到此檔案（非空）
6. 新增測試全部 pass，全套 353+ tests 不退步
