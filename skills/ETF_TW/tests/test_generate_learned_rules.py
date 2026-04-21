from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_learned_rules import build_stats_prompt, apply_rolling_logic


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
