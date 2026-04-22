#!/usr/bin/env python3
"""
strategy_audit.py — 策略影響力稽核

分析 decision_provenance.jsonl，回答：
  「切換投資策略是否真實影響決策鏈？還是只是裝飾？」

稽核維度：
  1. 策略分佈：各 base_strategy 出現次數
  2. 策略對齊率：strategy_aligned=True 的比例（per strategy）
  3. 策略與候選群組關係：每個策略實際選出哪些 group
  4. 策略與勝率：strategy_aligned=True vs False 的 T1/T3/T10 勝率
  5. 策略切換事件：連續決策中 base_strategy 改變的次數
  6. 評分差異：strategy_aligned=True 的平均 score vs False

輸出：dict（可用於 weekly report 或 CLI print）
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core.state_io import safe_load_jsonl


# ---------------------------------------------------------------------------
# Core audit function
# ---------------------------------------------------------------------------

def run_strategy_audit(provenance_path: Path) -> dict[str, Any]:
    """
    Read decision_provenance.jsonl and compute strategy influence metrics.

    Returns a dict with keys:
      strategy_distribution, alignment_rate_by_strategy,
      group_selection_by_strategy, win_rate_by_alignment,
      strategy_switch_count, avg_score_by_alignment
    """
    records = safe_load_jsonl(provenance_path) if provenance_path.exists() else []
    if not records:
        return _empty_audit()

    strategy_counts: dict[str, int] = defaultdict(int)
    aligned_counts: dict[str, int] = defaultdict(int)    # per strategy
    total_by_strategy: dict[str, int] = defaultdict(int)  # per strategy
    group_by_strategy: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    aligned_outcomes: dict[str, list[str]] = {'aligned': [], 'not_aligned': []}
    scores_by_alignment: dict[str, list[float]] = {'aligned': [], 'not_aligned': []}

    prev_strategy = None
    strategy_switches = 0

    for rec in records:
        snap = rec.get('strategy_snapshot', {})
        inputs = rec.get('inputs_digest', {})
        outputs = rec.get('outputs', {})

        base_strategy = snap.get('base_strategy') or inputs.get('base_strategy', 'unknown')
        strategy_aligned = outputs.get('strategy_aligned') if outputs.get('strategy_aligned') is not None else None
        # strategy_aligned is in candidate inside scan_result, exposed via outputs if stored
        # Fallback: check inputs_digest directly
        if strategy_aligned is None:
            strategy_aligned = inputs.get('strategy_aligned')

        score = outputs.get('score')
        symbol = outputs.get('symbol')
        group = None

        # Extract group from all_candidates_top3 matching the recommended symbol
        for c in outputs.get('all_candidates_top3', []):
            if c.get('symbol') == symbol:
                group = c.get('group')
                break

        strategy_counts[base_strategy] += 1
        total_by_strategy[base_strategy] += 1
        if strategy_aligned:
            aligned_counts[base_strategy] += 1
        if group:
            group_by_strategy[base_strategy][group] += 1

        # Strategy switches
        if prev_strategy is not None and prev_strategy != base_strategy:
            strategy_switches += 1
        prev_strategy = base_strategy

        # Outcomes by alignment
        verdict = _extract_verdict(rec)
        alignment_key = 'aligned' if strategy_aligned else 'not_aligned'
        if verdict:
            aligned_outcomes[alignment_key].append(verdict)
        if score is not None:
            scores_by_alignment[alignment_key].append(float(score))

    # Compute alignment rates
    alignment_rate: dict[str, float | None] = {}
    for strat, total in total_by_strategy.items():
        alignment_rate[strat] = round(aligned_counts[strat] / total, 3) if total > 0 else None

    # Win rates by alignment
    win_rate_by_alignment = {
        key: _win_rate(verdicts)
        for key, verdicts in aligned_outcomes.items()
    }

    # Average scores
    avg_score = {
        key: round(sum(s) / len(s), 2) if s else None
        for key, s in scores_by_alignment.items()
    }

    # Normalize group_by_strategy to regular dicts
    group_selection = {
        strat: dict(sorted(groups.items(), key=lambda x: -x[1]))
        for strat, groups in group_by_strategy.items()
    }

    return {
        'total_records': len(records),
        'strategy_distribution': dict(sorted(strategy_counts.items(), key=lambda x: -x[1])),
        'alignment_rate_by_strategy': alignment_rate,
        'group_selection_by_strategy': group_selection,
        'win_rate_by_alignment': win_rate_by_alignment,
        'strategy_switch_count': strategy_switches,
        'avg_score_by_alignment': avg_score,
        'sample_counts_by_alignment': {
            k: len(v) for k, v in aligned_outcomes.items()
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_verdict(rec: dict) -> str | None:
    """Extract the most informative verdict from a provenance record."""
    final = rec.get('outcome_final')
    if final and final.get('verdict'):
        return final['verdict']
    # Fall back to T10 → T3 → T1
    lc = rec.get('review_lifecycle', {})
    for window in ('T10', 'T3', 'T1'):
        entry = lc.get(window)
        if entry and entry.get('verdict') and entry['verdict'] not in ('skip', 'observed'):
            return entry['verdict']
    return None


def _win_rate(verdicts: list[str]) -> dict:
    total = len(verdicts)
    if total == 0:
        return {'total': 0, 'win_rate': None}
    wins = sum(1 for v in verdicts if v == 'win')
    losses = sum(1 for v in verdicts if v == 'loss')
    flats = sum(1 for v in verdicts if v == 'flat')
    return {
        'total': total,
        'win': wins,
        'loss': losses,
        'flat': flats,
        'win_rate': round(wins / total, 3),
    }


def _empty_audit() -> dict[str, Any]:
    return {
        'total_records': 0,
        'strategy_distribution': {},
        'alignment_rate_by_strategy': {},
        'group_selection_by_strategy': {},
        'win_rate_by_alignment': {},
        'strategy_switch_count': 0,
        'avg_score_by_alignment': {},
        'sample_counts_by_alignment': {},
    }


# ---------------------------------------------------------------------------
# Markdown formatter (for weekly report injection)
# ---------------------------------------------------------------------------

def format_strategy_audit_section(audit: dict) -> str:
    """Format strategy audit results as a Markdown section for weekly reports."""
    if audit['total_records'] == 0:
        return '\n## 策略影響力稽核\n\n（尚無決策記錄）\n'

    lines = ['', '## 策略影響力稽核', '']

    # Distribution
    lines.append('**策略分佈**')
    for strat, count in audit['strategy_distribution'].items():
        rate = audit['alignment_rate_by_strategy'].get(strat)
        rate_str = f'{rate:.0%}' if rate is not None else 'N/A'
        lines.append(f'- {strat}：{count} 筆，對齊率 {rate_str}')
    lines.append('')

    # Strategy switches
    lines.append(f'**策略切換次數（累計）**：{audit["strategy_switch_count"]} 次')
    lines.append('')

    # Group selection
    lines.append('**各策略實際選出群組（Top 2）**')
    for strat, groups in audit['group_selection_by_strategy'].items():
        top2 = list(groups.items())[:2]
        top2_str = '、'.join(f'{g}({n})' for g, n in top2) if top2 else '—'
        lines.append(f'- {strat}：{top2_str}')
    lines.append('')

    # Win rate by alignment
    lines.append('**策略對齊 vs 非對齊勝率**')
    lines.append('| 對齊狀態 | 樣本數 | 勝率 | 敗率 | 平均評分 |')
    lines.append('|----------|--------|------|------|----------|')
    for key, label in [('aligned', '策略對齊'), ('not_aligned', '未對齊')]:
        wr = audit['win_rate_by_alignment'].get(key, {})
        total = wr.get('total', 0)
        win_rate = f"{wr['win_rate']:.0%}" if wr.get('win_rate') is not None else 'N/A'
        loss_rate = f"{wr.get('loss', 0) / total:.0%}" if total > 0 else 'N/A'
        avg_sc = audit['avg_score_by_alignment'].get(key)
        avg_sc_str = f'{avg_sc:.1f}' if avg_sc is not None else 'N/A'
        lines.append(f'| {label} | {total} | {win_rate} | {loss_rate} | {avg_sc_str} |')
    lines.append('')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    import json
    from etf_core import context

    STATE = context.get_state_dir()
    provenance_path = STATE / 'decision_provenance.jsonl'

    audit = run_strategy_audit(provenance_path)
    print(json.dumps(audit, ensure_ascii=False, indent=2))

    section = format_strategy_audit_section(audit)
    print('\n--- Markdown Preview ---')
    print(section)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
