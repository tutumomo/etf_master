# Learned Rules Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓每週復盤統計透過 AI Bridge 歸納成具體規則，寫入 `wiki/learned-rules.md` 作為 AI 決策的第 16 個輸入源，形成 autoresearch 式的完整閉環。

**Architecture:** `generate_learned_rules.py` 負責三件事：組統計摘要 prompt 注入 `ai_decision_request.json`、從 `ai_decision_response.json` 解析 `reasoning.learned_rules`、執行版本化滾動後寫 `wiki/learned-rules.md`。每週六週報末尾觸發，`generate_ai_decision_request.py` 讀取結果作為第 16 個輸入源。

**Tech Stack:** Python 3.14, pathlib, json, zoneinfo, etf_core.state_io, pytest

---

## File Map

| 動作 | 路徑 | 職責 |
|------|------|------|
| Create | `skills/ETF_TW/scripts/generate_learned_rules.py` | 核心邏輯：組 prompt、解析 LLM 輸出、滾動邏輯、寫 wiki |
| Create | `skills/ETF_TW/tests/test_generate_learned_rules.py` | 單元測試（純函數，無 I/O） |
| Modify | `skills/ETF_TW/scripts/generate_decision_quality_weekly.py` | 週報末尾呼叫 `generate_learned_rules.run()` |
| Modify | `skills/ETF_TW/scripts/generate_ai_decision_request.py` | `wiki_context` 加入第 16 個欄位 `learned_rules` |
| Modify | `skills/ETF_TW/scripts/generate_ai_agent_response.py` | `_build_agent_reasoning` 的 `reasoning` dict 加入 `learned_rules` 欄位輸出 |

---

## Task 1：`generate_learned_rules.py` — 統計摘要組裝（純函數）

**Files:**
- Create: `skills/ETF_TW/scripts/generate_learned_rules.py`
- Create: `skills/ETF_TW/tests/test_generate_learned_rules.py`

- [ ] **Step 1: 建立測試檔，寫第一個失敗測試**

```python
# skills/ETF_TW/tests/test_generate_learned_rules.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_learned_rules import build_stats_prompt

def test_build_stats_prompt_includes_rule_engine_stats():
    chain_breakdown = {
        "rule_engine": {"total": 12, "win": 7, "loss": 3, "flat": 2, "win_rate": 0.583},
        "ai_bridge":   {"total": 10, "win": 4, "loss": 4, "flat": 2, "win_rate": 0.400},
        "tier1_consensus": {"total": 5, "win": 4, "loss": 1, "flat": 0, "win_rate": 0.800},
    }
    week_stats = {
        "top_wins":   [{"symbol": "0050", "window": "T3", "return_pct": 2.1}],
        "top_losses": [{"symbol": "00878", "window": "T1", "return_pct": -1.8}],
    }
    existing_rules = []
    prompt = build_stats_prompt(chain_breakdown, week_stats, existing_rules)
    assert "58.3%" in prompt or "58%" in prompt   # rule_engine win_rate
    assert "0050" in prompt
    assert "00878" in prompt
    assert "JSON array" in prompt
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py::test_build_stats_prompt_includes_rule_engine_stats -v
```
Expected: `ImportError` 或 `ModuleNotFoundError`（檔案尚未存在）

- [ ] **Step 3: 建立 `generate_learned_rules.py`，實作 `build_stats_prompt`**

```python
# skills/ETF_TW/scripts/generate_learned_rules.py
"""
generate_learned_rules.py — EVOLUTION-01

每週六週報後執行。流程：
1. 讀 chain_breakdown + top_wins/losses → 組統計摘要 prompt
2. 注入 ai_decision_request.json wiki_context.learned_rules_draft
3. 呼叫 generate_ai_agent_response.py
4. 從 ai_decision_response.json 取 reasoning.learned_rules
5. 執行版本化滾動 → 寫 wiki/learned-rules.md + state/learned_rules_meta.json

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/generate_learned_rules.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core import context
from etf_core.state_io import safe_load_json, safe_load_jsonl, atomic_save_json

TW_TZ = ZoneInfo("Asia/Taipei")
MIN_SAMPLES = 5   # 樣本不足時跳過 LLM 呼叫
MAX_RULES = 15
STALE_WEEKS = 4


def _pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%"


def build_stats_prompt(
    chain_breakdown: dict,
    week_stats: dict,
    existing_rules: list[dict],
) -> str:
    """純函數：給定統計數據，回傳注入 AI Bridge 的 prompt 字串。"""
    rb = chain_breakdown or {}
    rule_b = rb.get("rule_engine", {})
    ai_b = rb.get("ai_bridge", {})
    tier1_b = rb.get("tier1_consensus", {})

    wins_txt = "\n".join(
        f"  - {w['symbol']} / {w['window']} / +{w['return_pct']}%"
        for w in (week_stats.get("top_wins") or [])
    ) or "  （無）"
    losses_txt = "\n".join(
        f"  - {l['symbol']} / {l['window']} / {l['return_pct']}%"
        for l in (week_stats.get("top_losses") or [])
    ) or "  （無）"

    existing_txt = "\n".join(
        f"{r['rule_id']}: {r['rule_text']}（出現{r['count']}次，{r['status']}）"
        for r in existing_rules
    ) or "  （尚無既有規則）"

    return f"""你是 ETF_Master 的決策品質分析師。
根據以下本週復盤統計，歸納出 1–5 條具體可執行的投資決策規則。

【本週統計】
- rule_engine: 總計 {rule_b.get('total', 0)} 筆, 勝率 {_pct(rule_b.get('win_rate'))}, 敗率 {_pct(rule_b.get('loss', 0) / rule_b['total'] if rule_b.get('total') else None)}
- ai_bridge: 總計 {ai_b.get('total', 0)} 筆, 勝率 {_pct(ai_b.get('win_rate'))}, 敗率 {_pct(ai_b.get('loss', 0) / ai_b['total'] if ai_b.get('total') else None)}
- tier1_consensus: 總計 {tier1_b.get('total', 0)} 筆, 勝率 {_pct(tier1_b.get('win_rate'))}
- 本週最準確:
{wins_txt}
- 本週最大失誤:
{losses_txt}

【現有規則庫摘要（避免重複）】
{existing_txt}

【輸出格式】（純 JSON array，無其他文字）
[
  {{
    "rule_text": "具體規則描述",
    "source_stats": "支撐此規則的統計數據摘要",
    "is_existing_rule_id": null
  }}
]
若要強化既有規則，將 is_existing_rule_id 填入對應 RULE-ID（如 "RULE-001"）。"""
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py::test_build_stats_prompt_includes_rule_engine_stats -v
```
Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_learned_rules.py \
        skills/ETF_TW/tests/test_generate_learned_rules.py
git commit -m "feat(evolution): generate_learned_rules.py — build_stats_prompt"
```

---

## Task 2：滾動邏輯純函數（apply_rolling_logic）

**Files:**
- Modify: `skills/ETF_TW/scripts/generate_learned_rules.py`
- Modify: `skills/ETF_TW/tests/test_generate_learned_rules.py`

- [ ] **Step 1: 新增測試**

```python
# 加到 test_generate_learned_rules.py
from generate_learned_rules import apply_rolling_logic

def _make_meta(rules: list[dict]) -> dict:
    return {"rules": rules}

def test_new_rule_is_tentative():
    meta = _make_meta([])
    new_items = [{"rule_text": "買入前確認 RSI < 50", "source_stats": "win_rate=60%", "is_existing_rule_id": None}]
    week_key = "2026-W17"
    result = apply_rolling_logic(meta, new_items, week_key)
    assert len(result["rules"]) == 1
    r = result["rules"][0]
    assert r["status"] == "tentative"
    assert r["count"] == 1
    assert r["first_seen"] == week_key
    assert r["last_confirmed"] == week_key

def test_existing_rule_becomes_active_after_second_week():
    meta = _make_meta([{
        "rule_id": "RULE-001", "rule_text": "買入前確認 RSI < 50",
        "source_stats": "win_rate=60%", "count": 1,
        "first_seen": "2026-W16", "last_confirmed": "2026-W16", "status": "tentative"
    }])
    new_items = [{"rule_text": "買入前確認 RSI < 50", "source_stats": "win_rate=62%", "is_existing_rule_id": "RULE-001"}]
    result = apply_rolling_logic(meta, new_items, "2026-W17")
    r = result["rules"][0]
    assert r["status"] == "active"
    assert r["count"] == 2
    assert r["last_confirmed"] == "2026-W17"

def test_rule_becomes_stale_after_four_weeks():
    meta = _make_meta([{
        "rule_id": "RULE-001", "rule_text": "測試規則",
        "source_stats": "x", "count": 3,
        "first_seen": "2026-W10", "last_confirmed": "2026-W12", "status": "active"
    }])
    # W17 - W12 = 5 週，超過 STALE_WEEKS=4
    result = apply_rolling_logic(meta, [], "2026-W17")
    assert result["rules"][0]["status"] == "stale"

def test_max_15_rules_removes_oldest_stale():
    stale_rules = [
        {"rule_id": f"RULE-{i:03d}", "rule_text": f"rule {i}", "source_stats": "",
         "count": 1, "first_seen": "2026-W01", "last_confirmed": "2026-W01", "status": "stale"}
        for i in range(1, 16)  # 15 stale rules
    ]
    meta = _make_meta(stale_rules)
    new_items = [{"rule_text": "新規則", "source_stats": "新統計", "is_existing_rule_id": None}]
    result = apply_rolling_logic(meta, new_items, "2026-W17")
    assert len(result["rules"]) == 15
    ids = [r["rule_id"] for r in result["rules"]]
    assert "RULE-001" not in ids   # oldest stale evicted
    assert any(r["rule_text"] == "新規則" for r in result["rules"])
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py -k "rolling or stale or active or tentative or max_15" -v
```
Expected: 4 個 `FAILED`（`apply_rolling_logic` 未定義）

- [ ] **Step 3: 實作 `apply_rolling_logic`**

在 `generate_learned_rules.py` 末尾追加：

```python
def _week_diff(week_a: str, week_b: str) -> int:
    """回傳 week_b - week_a 的週數差（week_b 較新為正）。"""
    def _monday(wk: str) -> date:
        yr, wn = wk.split("-W")
        jan4 = date(int(yr), 1, 4)
        return jan4 - __import__('datetime').timedelta(days=jan4.weekday()) + \
               __import__('datetime').timedelta(weeks=int(wn) - 1)
    return (_monday(week_b) - _monday(week_a)).days // 7


def _next_rule_id(existing_ids: list[str]) -> str:
    nums = []
    for rid in existing_ids:
        try:
            nums.append(int(rid.replace("RULE-", "")))
        except ValueError:
            pass
    return f"RULE-{(max(nums) + 1 if nums else 1):03d}"


def apply_rolling_logic(
    meta: dict,
    new_items: list[dict],
    current_week: str,
) -> dict:
    """
    純函數：給定現有 meta 和本週 LLM 新規則，回傳更新後的 meta。

    meta 結構：{"rules": [{"rule_id", "rule_text", "source_stats",
                            "count", "first_seen", "last_confirmed", "status"}, ...]}
    """
    import copy
    rules: list[dict] = copy.deepcopy(meta.get("rules") or [])

    # 1. 標記 stale：超過 STALE_WEEKS 未出現
    for r in rules:
        if r.get("status") in ("tentative", "active"):
            diff = _week_diff(r["last_confirmed"], current_week)
            if diff > STALE_WEEKS:
                r["status"] = "stale"

    # 2. 處理本週新規則
    existing_ids = [r["rule_id"] for r in rules]
    for item in new_items:
        existing_id = item.get("is_existing_rule_id")
        if existing_id:
            # 強化既有規則
            for r in rules:
                if r["rule_id"] == existing_id:
                    r["count"] += 1
                    r["last_confirmed"] = current_week
                    r["source_stats"] = item.get("source_stats", r["source_stats"])
                    if r["count"] >= 2:
                        r["status"] = "active"
                    break
        else:
            # 全新規則
            new_id = _next_rule_id(existing_ids)
            existing_ids.append(new_id)
            rules.append({
                "rule_id": new_id,
                "rule_text": item["rule_text"],
                "source_stats": item.get("source_stats", ""),
                "count": 1,
                "first_seen": current_week,
                "last_confirmed": current_week,
                "status": "tentative",
            })

    # 3. 超過上限：淘汰最舊 stale（按 last_confirmed 升序）
    if len(rules) > MAX_RULES:
        stale = sorted(
            [r for r in rules if r["status"] == "stale"],
            key=lambda r: r["last_confirmed"],
        )
        to_remove = len(rules) - MAX_RULES
        remove_ids = {r["rule_id"] for r in stale[:to_remove]}
        rules = [r for r in rules if r["rule_id"] not in remove_ids]

    return {"rules": rules}
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py -v
```
Expected: 全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_learned_rules.py \
        skills/ETF_TW/tests/test_generate_learned_rules.py
git commit -m "feat(evolution): apply_rolling_logic — 版本化滾動邏輯"
```

---

## Task 3：`format_learned_rules_md` 與 `parse_llm_output`

**Files:**
- Modify: `skills/ETF_TW/scripts/generate_learned_rules.py`
- Modify: `skills/ETF_TW/tests/test_generate_learned_rules.py`

- [ ] **Step 1: 新增測試**

```python
# 加到 test_generate_learned_rules.py
from generate_learned_rules import format_learned_rules_md, parse_llm_output

def test_format_learned_rules_md_contains_rule_text():
    meta = {"rules": [{
        "rule_id": "RULE-001", "rule_text": "高波動時延後買入",
        "source_stats": "win_rate=32%", "count": 3,
        "first_seen": "2026-W15", "last_confirmed": "2026-W17", "status": "active"
    }]}
    md = format_learned_rules_md(meta, generated_at="2026-04-22T09:05:00+08:00")
    assert "RULE-001" in md
    assert "高波動時延後買入" in md
    assert "active" in md
    assert "2026-W17" in md

def test_format_learned_rules_md_excludes_stale():
    meta = {"rules": [
        {"rule_id": "RULE-001", "rule_text": "active rule", "source_stats": "",
         "count": 2, "first_seen": "2026-W10", "last_confirmed": "2026-W16", "status": "active"},
        {"rule_id": "RULE-002", "rule_text": "stale rule", "source_stats": "",
         "count": 1, "first_seen": "2026-W05", "last_confirmed": "2026-W08", "status": "stale"},
    ]}
    md = format_learned_rules_md(meta, generated_at="2026-04-22T09:05:00+08:00")
    assert "active rule" in md
    assert "stale rule" not in md

def test_parse_llm_output_valid():
    raw = '[{"rule_text": "RSI > 70 不追高", "source_stats": "...", "is_existing_rule_id": null}]'
    result = parse_llm_output(raw)
    assert len(result) == 1
    assert result[0]["rule_text"] == "RSI > 70 不追高"

def test_parse_llm_output_invalid_returns_empty():
    assert parse_llm_output("not json") == []
    assert parse_llm_output('{"key": "val"}') == []  # dict not array
    assert parse_llm_output("") == []

def test_parse_llm_output_strips_markdown_fences():
    raw = '```json\n[{"rule_text": "test", "source_stats": "", "is_existing_rule_id": null}]\n```'
    result = parse_llm_output(raw)
    assert len(result) == 1
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py -k "format or parse" -v
```
Expected: `FAILED`（函數未定義）

- [ ] **Step 3: 實作兩個函數**

在 `generate_learned_rules.py` 末尾追加：

```python
def parse_llm_output(raw: str) -> list[dict]:
    """解析 LLM 回傳的 JSON array。非法輸出回傳空 list。"""
    if not raw:
        return []
    text = raw.strip()
    # 去掉 markdown code fence
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        ).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    result = []
    for item in parsed:
        if isinstance(item, dict) and "rule_text" in item:
            result.append({
                "rule_text": str(item.get("rule_text", "")),
                "source_stats": str(item.get("source_stats", "")),
                "is_existing_rule_id": item.get("is_existing_rule_id"),
            })
    return result


def format_learned_rules_md(meta: dict, generated_at: str) -> str:
    """將 meta 轉成 wiki/learned-rules.md 格式（stale 規則不輸出）。"""
    active_rules = [r for r in (meta.get("rules") or []) if r.get("status") != "stale"]
    lines = [
        "## 學習規則庫",
        f"generated_at: {generated_at}",
        "",
    ]
    for r in active_rules:
        lines += [
            f"### {r['rule_id']}",
            f"- **規則**：{r['rule_text']}",
            f"- **來源統計**：{r['source_stats']}",
            f"- **出現次數**：{r['count']}",
            f"- **首次出現**：{r['first_seen']}",
            f"- **最後確認**：{r['last_confirmed']}",
            f"- **狀態**：{r['status']}",
            "",
        ]
    if not active_rules:
        lines.append("（本週尚無有效規則）")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py -v
```
Expected: 全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_learned_rules.py \
        skills/ETF_TW/tests/test_generate_learned_rules.py
git commit -m "feat(evolution): parse_llm_output + format_learned_rules_md"
```

---

## Task 4：`run()` — I/O 整合與 AI Bridge 呼叫

**Files:**
- Modify: `skills/ETF_TW/scripts/generate_learned_rules.py`
- Modify: `skills/ETF_TW/tests/test_generate_learned_rules.py`

- [ ] **Step 1: 新增測試（I/O + 跳過邏輯）**

```python
# 加到 test_generate_learned_rules.py
import json
from generate_learned_rules import run, MIN_SAMPLES

def test_run_skips_when_insufficient_samples(tmp_path):
    """樣本不足時不寫任何檔案。"""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    quality_report = {
        "chain_breakdown": {
            "rule_engine": {"total": 3, "win_rate": 0.5},
        }
    }
    (state_dir / "decision_quality_report.json").write_text(
        json.dumps(quality_report), encoding="utf-8"
    )
    result = run(state_dir=state_dir, wiki_dir=wiki_dir, dry_run=True)
    assert result["skipped"] is True
    assert result["reason"] == "insufficient_samples"
    assert not (wiki_dir / "learned-rules.md").exists()

def test_run_dry_run_does_not_write_wiki(tmp_path):
    """dry_run=True 時不寫 wiki，但回傳 would_write。"""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    quality_report = {
        "chain_breakdown": {
            "rule_engine": {"total": 10, "win": 6, "loss": 3, "flat": 1, "win_rate": 0.6},
            "ai_bridge":   {"total": 8,  "win": 4, "loss": 3, "flat": 1, "win_rate": 0.5},
            "tier1_consensus": {"total": 5, "win": 4, "loss": 1, "flat": 0, "win_rate": 0.8},
        }
    }
    (state_dir / "decision_quality_report.json").write_text(
        json.dumps(quality_report), encoding="utf-8"
    )
    # 模擬 ai_decision_response 已有 learned_rules
    response = {
        "reasoning": {
            "learned_rules": json.dumps([
                {"rule_text": "測試規則", "source_stats": "win_rate=60%", "is_existing_rule_id": None}
            ])
        }
    }
    (state_dir / "ai_decision_response.json").write_text(
        json.dumps(response), encoding="utf-8"
    )
    result = run(state_dir=state_dir, wiki_dir=wiki_dir, dry_run=True)
    assert result["skipped"] is False
    assert "would_write" in result
    assert not (wiki_dir / "learned-rules.md").exists()
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py -k "run_" -v
```
Expected: `FAILED`（`run` 未定義）

- [ ] **Step 3: 實作 `run()` 函數**

在 `generate_learned_rules.py` 末尾追加：

```python
def _inject_learned_rules_draft_into_request(state_dir: Path, prompt: str) -> None:
    """將 learned_rules_draft 注入現有 ai_decision_request.json 的 wiki_context。"""
    req_path = state_dir / "ai_decision_request.json"
    payload = safe_load_json(req_path, {})
    wiki_ctx = payload.get("wiki_context") or {}
    wiki_ctx["learned_rules_draft"] = prompt
    payload["wiki_context"] = wiki_ctx
    atomic_save_json(req_path, payload)


def run(
    state_dir: Path | None = None,
    wiki_dir: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """
    執行完整的 learned-rules 更新流程。

    回傳:
        {"skipped": True, "reason": str}  — 跳過時
        {"skipped": False, "applied": bool, "rules_count": int, "would_write": str}
    """
    if state_dir is None:
        state_dir = context.get_state_dir()
    if wiki_dir is None:
        # profile-level wiki（generate_learned_rules.py 在 scripts/，parents[3] = profile root）
        wiki_dir = Path(__file__).resolve().parents[3] / "wiki"

    quality_report = safe_load_json(state_dir / "decision_quality_report.json", {})
    chain_breakdown = quality_report.get("chain_breakdown", {})

    # 樣本數檢查：以 rule_engine total 為基準
    rule_total = (chain_breakdown.get("rule_engine") or {}).get("total", 0)
    if rule_total < MIN_SAMPLES:
        print(f"[learned_rules] 跳過：rule_engine 樣本數 {rule_total} < {MIN_SAMPLES}")
        return {"skipped": True, "reason": "insufficient_samples"}

    # 讀本週統計
    provenance = safe_load_jsonl(state_dir / "decision_provenance.jsonl")
    today = datetime.now(tz=TW_TZ).date()
    iso_year, iso_week, _ = today.isocalendar()
    current_week = f"{iso_year}-W{iso_week:02d}"

    # 簡易本週 top_wins/losses（從 weekly report 已計算的 quality_report 取，避免重複計算）
    week_stats: dict = {
        "top_wins": quality_report.get("top_wins_latest") or [],
        "top_losses": quality_report.get("top_losses_latest") or [],
    }

    # 讀現有規則庫 meta
    meta = safe_load_json(state_dir / "learned_rules_meta.json", {"rules": []})
    existing_rules = meta.get("rules", [])

    # 組 prompt 注入 request
    prompt = build_stats_prompt(chain_breakdown, week_stats, existing_rules)
    _inject_learned_rules_draft_into_request(state_dir, prompt)

    # 讀 ai_decision_response（由呼叫方先執行 generate_ai_agent_response.py）
    response = safe_load_json(state_dir / "ai_decision_response.json", {})
    raw_learned = (response.get("reasoning") or {}).get("learned_rules", "")

    if not raw_learned:
        print("[learned_rules] ai_decision_response.reasoning.learned_rules 為空，跳過本週更新")
        return {"skipped": False, "applied": False, "rules_count": len(existing_rules), "reason": "no_llm_output"}

    new_items = parse_llm_output(raw_learned)
    if not new_items:
        print("[learned_rules] LLM 輸出解析失敗，跳過")
        return {"skipped": False, "applied": False, "rules_count": len(existing_rules), "reason": "parse_failed"}

    updated_meta = apply_rolling_logic(meta, new_items, current_week)
    now_str = datetime.now(tz=TW_TZ).isoformat()
    md_content = format_learned_rules_md(updated_meta, generated_at=now_str)

    if dry_run:
        return {"skipped": False, "applied": False, "would_write": md_content,
                "rules_count": len(updated_meta["rules"])}

    # 寫 wiki + meta
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "learned-rules.md").write_text(md_content, encoding="utf-8")
    updated_meta["last_updated"] = now_str
    atomic_save_json(state_dir / "learned_rules_meta.json", updated_meta)

    active = sum(1 for r in updated_meta["rules"] if r["status"] != "stale")
    print(f"[learned_rules] 完成 — {active} 條有效規則寫入 wiki/learned-rules.md")
    return {"skipped": False, "applied": True, "rules_count": len(updated_meta["rules"])}


def main() -> None:
    parser = argparse.ArgumentParser(description="產出 wiki/learned-rules.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_learned_rules.py -v
```
Expected: 全部 `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_learned_rules.py \
        skills/ETF_TW/tests/test_generate_learned_rules.py
git commit -m "feat(evolution): generate_learned_rules.run() — I/O 整合"
```

---

## Task 5：`generate_ai_agent_response.py` — 加入 `learned_rules` 輸出欄位

**Files:**
- Modify: `skills/ETF_TW/scripts/generate_ai_agent_response.py:155-162`

- [ ] **Step 1: 讀檔確認 reasoning dict 位置**

```bash
grep -n "reasoning = {" ~/.hermes/profiles/etf_master/skills/ETF_TW/scripts/generate_ai_agent_response.py
```
Expected: 顯示行號（約 155 行附近）

- [ ] **Step 2: 在 reasoning dict 中加入 `learned_rules` 欄位**

找到 `_build_agent_reasoning` 中「資料不足 fallback」的 reasoning dict（約 155 行）：

```python
        reasoning = {
            'market_context_summary': market_summary_final,
            'position_context_summary': pre_reasoning.get('position_context_summary') or group_summary,
            'risk_context_summary': risk_summary_final,
            'reasoning_source': pre_reasoning.get('source', 'inline'),
        }
```

改為：

```python
        reasoning = {
            'market_context_summary': market_summary_final,
            'position_context_summary': pre_reasoning.get('position_context_summary') or group_summary,
            'risk_context_summary': risk_summary_final,
            'reasoning_source': pre_reasoning.get('source', 'inline'),
            'learned_rules': '',  # 資料不足時空字串
        }
```

同樣找到「正常流程」的 reasoning dict（`return candidate, reasoning, ...` 前方，約 340–356 行），加入同一欄位：

```python
    learned_rules_draft = str(wiki_context.get('learned_rules_draft') or '')
    # ... 在 return 前組 reasoning dict，加入：
    #   'learned_rules': <LLM 歸納的規則 JSON string，或空字串>
```

具體：在 `_build_agent_reasoning` 最後的 `return candidate, reasoning, ...` 前，找到 reasoning dict 的最終組裝，加入：

```python
    reasoning['learned_rules'] = learned_rules_draft  # 傳遞給 generate_learned_rules 解析
```

- [ ] **Step 3: 跑全套測試確認無 regression**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```
Expected: `385 passed`（或更多，0 failed）

- [ ] **Step 4: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_ai_agent_response.py
git commit -m "feat(evolution): generate_ai_agent_response 加入 learned_rules 欄位"
```

---

## Task 6：`generate_ai_decision_request.py` — 第 16 個輸入源

**Files:**
- Modify: `skills/ETF_TW/scripts/generate_ai_decision_request.py:193-200`

- [ ] **Step 1: 讀現有 wiki_context 組裝位置**

```bash
grep -n "wiki_context\|learned_rules" \
  ~/.hermes/profiles/etf_master/skills/ETF_TW/scripts/generate_ai_decision_request.py
```

- [ ] **Step 2: 在 `_resolve_wiki_roots` 後加入 `_read_learned_rules` helper，並注入 wiki_context**

在 `generate_ai_decision_request.py` 的 `_read_first` 函數後方加入：

```python
def _read_learned_rules(wiki_roots: list[Path]) -> str:
    """讀取 wiki/learned-rules.md，不存在或空回傳空字串（不阻斷）。"""
    paths = [root / "learned-rules.md" for root in wiki_roots]
    return _read_first(paths)
```

在 `generate_request_payload_from_state_dir` 的 `wiki_context` dict 中加入第 16 個欄位：

```python
    payload['wiki_context'] = {
        "market_view": market_view_wiki,
        "risk_signal": risk_signal_wiki,
        "investment_strategies": investment_strategies_wiki,
        "undervalued_ranking": undervalued_ranking_wiki,
        "entities": entity_wiki_summaries,
        "learned_rules": _read_learned_rules(wiki_roots),   # 第 16 個輸入源
    }
```

- [ ] **Step 3: 跑全套測試確認無 regression**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```
Expected: `385 passed`，0 failed

- [ ] **Step 4: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_ai_decision_request.py
git commit -m "feat(evolution): generate_ai_decision_request 加入 learned_rules 第 16 個輸入源"
```

---

## Task 7：`generate_decision_quality_weekly.py` — 週報末尾接入

**Files:**
- Modify: `skills/ETF_TW/scripts/generate_decision_quality_weekly.py:220-252`

- [ ] **Step 1: 在 `main()` 末尾，`auto_calibrate_thresholds` 呼叫後加入 `generate_learned_rules`**

找到現有的 calibrate 呼叫區段：

```python
    # 週報完成後執行門檻校正
    try:
        from auto_calibrate_thresholds import run as calibrate
        calibrate()
    except Exception as exc:
        print(f"[calibrate] 跳過（{exc}）")
```

在其後追加：

```python
    # 門檻校正完成後執行規則學習閉環
    try:
        from generate_learned_rules import run as gen_rules
        result = gen_rules()
        if result.get("skipped"):
            print(f"[learned_rules] 跳過：{result.get('reason')}")
        elif result.get("applied"):
            print(f"[learned_rules] 完成：{result.get('rules_count')} 條規則")
    except Exception as exc:
        print(f"[learned_rules] 跳過（{exc}）")
```

- [ ] **Step 2: 跑全套測試確認無 regression**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```
Expected: `385 passed`，0 failed

- [ ] **Step 3: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_decision_quality_weekly.py
git commit -m "feat(evolution): 週報末尾接入 generate_learned_rules"
```

---

## Task 8：端對端驗證

- [ ] **Step 1: 確認 `wiki_roots` 路徑正確**

```bash
AGENT_ID=etf_master \
  ~/.hermes/profiles/etf_master/skills/ETF_TW/.venv/bin/python3 -c "
import sys; sys.path.insert(0, 'scripts')
from generate_ai_decision_request import _resolve_wiki_roots, _read_learned_rules
roots = _resolve_wiki_roots()
print('wiki roots:', roots)
print('learned_rules:', repr(_read_learned_rules(roots)[:100]))
"
```
Expected: `wiki roots` 包含 profile wiki 路徑，`learned_rules` 為空字串（md 尚未存在）

- [ ] **Step 2: dry-run 驗證整體流程**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 scripts/generate_learned_rules.py --dry-run
```
Expected:
- 若樣本不足：`[learned_rules] 跳過：rule_engine 樣本數 X < 5`
- 若 response 無 learned_rules：`ai_decision_response.reasoning.learned_rules 為空，跳過本週更新`

- [ ] **Step 3: 跑全套測試最終確認**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```
Expected: `≥ 385 passed`，0 failed

- [ ] **Step 4: 更新 CLAUDE.md — 補充 learned-rules 相關說明**

在 `CLAUDE.md` 的 Important Rules for Code Changes 區塊加入：

```
19. **Wiki learned-rules 主寫層**：`wiki/learned-rules.md` 由 `generate_learned_rules.py` 自動產生，不要手動編輯。規則 metadata 在 `state/learned_rules_meta.json`。
```

- [ ] **Step 5: 打最終 commit + tag**

```bash
cd ~/.hermes/profiles/etf_master
git add CLAUDE.md
git commit -m "feat(evolution): learned-rules 閉環完成 — autoresearch 式自我迭代

- generate_learned_rules.py：統計摘要 → AI Bridge → 版本化滾動 → wiki
- generate_ai_decision_request.py：learned_rules 成為第 16 個輸入源
- generate_ai_agent_response.py：reasoning 輸出 learned_rules 欄位
- generate_decision_quality_weekly.py：週報末尾自動觸發
- 測試覆蓋：9 個純函數測試全通

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git tag v1.4.8
```
