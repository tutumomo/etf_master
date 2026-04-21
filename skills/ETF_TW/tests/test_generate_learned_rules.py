from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_learned_rules import build_stats_prompt, apply_rolling_logic, format_learned_rules_md, parse_llm_output


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


# ── Task 2: apply_rolling_logic ───────────────────────────────────────────────

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


# ── Task 3: format_learned_rules_md + parse_llm_output ───────────────────────

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


# ── Task 4: run() ─────────────────────────────────────────────────────────────

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
