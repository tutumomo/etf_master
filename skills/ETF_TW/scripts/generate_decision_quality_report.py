#!/usr/bin/env python3
"""
generate_decision_quality_report.py — QUALITY-01

Reads ai_decision_outcome.jsonl and writes decision_quality_report.json.
Pure generate_report() function for testability + main() for CLI usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from etf_core.context import get_state_dir
from etf_core.state_io import safe_load_jsonl, atomic_save_json


def generate_report(records: list[dict]) -> dict:
    """Pure function: compute decision quality metrics from outcome records."""
    total = len(records)

    # strategy_alignment_rate — denominator is records with the key present
    aligned_records = [r for r in records if r.get("strategy_alignment") is not None]
    aligned_true = sum(1 for r in aligned_records if r.get("strategy_alignment") is True)
    strategy_alignment_rate = (
        round(aligned_true / len(aligned_records) * 100, 2) if aligned_records else 0.0
    )

    # confidence_distribution — skip records without confidence key
    confidence_dist = {"high": 0, "medium": 0, "low": 0}
    for r in records:
        conf = r.get("confidence")
        if conf is None:
            continue
        if conf >= 0.7:
            confidence_dist["high"] += 1
        elif conf >= 0.4:
            confidence_dist["medium"] += 1
        else:
            confidence_dist["low"] += 1

    # interception_rate — denominator is total records
    intercepted = sum(1 for r in records if r.get("pre_flight_intercepted") is True)
    interception_rate = round(intercepted / total * 100, 2) if total > 0 else 0.0

    # tier_distribution
    tier_dist = {"tier1": 0, "tier2": 0, "tier3": 0}
    for r in records:
        tier = r.get("tier")
        if tier == 1:
            tier_dist["tier1"] += 1
        elif tier == 2:
            tier_dist["tier2"] += 1
        elif tier == 3:
            tier_dist["tier3"] += 1

    last_updated = datetime.now(tz=ZoneInfo("Asia/Taipei")).isoformat()

    return {
        "strategy_alignment_rate": strategy_alignment_rate,
        "confidence_distribution": confidence_dist,
        "interception_rate": interception_rate,
        "tier_distribution": tier_dist,
        "win_rate": None,
        "total_decisions": total,
        "last_updated": last_updated,
    }


def main(outcome_path: Path | None = None, output_path: Path | None = None) -> None:
    state_dir = get_state_dir()
    if outcome_path is None:
        outcome_path = state_dir / "ai_decision_outcome.jsonl"
    if output_path is None:
        output_path = state_dir / "decision_quality_report.json"

    records = safe_load_jsonl(outcome_path)
    report = generate_report(records)
    atomic_save_json(output_path, report)
    print(f"[quality-report] Generated: {output_path} ({report['total_decisions']} decisions)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate decision quality report")
    parser.add_argument("--outcome", type=Path, default=None, help="Path to ai_decision_outcome.jsonl")
    parser.add_argument("--output", type=Path, default=None, help="Path to output decision_quality_report.json")
    args = parser.parse_args()
    main(outcome_path=args.outcome, output_path=args.output)
