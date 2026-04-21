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
