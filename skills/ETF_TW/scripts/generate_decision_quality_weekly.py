#!/usr/bin/env python3
"""
generate_decision_quality_weekly.py — 週報產出腳本

每週六 09:05 執行。讀取 decision_provenance.jsonl + decision_quality_report.json，
計算本週統計與雙鏈勝率，寫入 wiki/decision-weekly-YYYY-WNN.md
並同步更新 wiki/decision-quality-latest.md 供 AI Bridge 引用。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core.state_io import safe_load_json, safe_load_jsonl
from etf_core import context

TW_TZ = ZoneInfo('Asia/Taipei')

# Profile-level wiki (preferred) — same location used by generate_ai_decision_request.py
# Script at skills/ETF_TW/scripts/ → parents[0]=scripts, [1]=ETF_TW, [2]=skills, [3]=profile
WIKI_DIR = Path(__file__).resolve().parents[3] / 'wiki'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iso_week_key(d: date) -> str:
    """Return 'YYYY-WNN' ISO week string for date d."""
    iso_year, iso_week, _ = d.isocalendar()
    return f'{iso_year}-W{iso_week:02d}'


def _date_of_iso_week_start(week_key: str) -> date:
    """Return the Monday of the given ISO week key."""
    year_str, week_str = week_key.split('-W')
    jan4 = date(int(year_str), 1, 4)
    week_monday = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=int(week_str) - 1)
    return week_monday


def _parse_date(dt_str: str) -> date | None:
    try:
        return datetime.fromisoformat(dt_str).date()
    except (ValueError, TypeError):
        return None


def _in_week(dt_str: str, week_key: str) -> bool:
    """Return True if dt_str falls within the ISO week identified by week_key."""
    d = _parse_date(dt_str)
    if d is None:
        return False
    return iso_week_key(d) == week_key


# ---------------------------------------------------------------------------
# Stats collector
# ---------------------------------------------------------------------------

def collect_week_stats(records: list[dict], week_start: date) -> dict:
    """Aggregate per-week statistics from provenance records."""
    week_key = iso_week_key(week_start)

    new_decisions = 0
    t1_filled = 0
    t3_filled = 0
    t10_filled = 0
    finalized = 0
    top_wins = []
    top_losses = []

    for rec in records:
        created_at = rec.get('created_at', '')
        if _in_week(created_at, week_key):
            new_decisions += 1

        lc = rec.get('review_lifecycle', {})
        for window, counter_name in (('T1', 't1_filled'), ('T3', 't3_filled'), ('T10', 't10_filled')):
            slot = lc.get(window)
            if slot and _in_week(slot.get('reviewed_at', ''), week_key):
                if window == 'T1':
                    t1_filled += 1
                elif window == 'T3':
                    t3_filled += 1
                elif window == 'T10':
                    t10_filled += 1

        outcome = rec.get('outcome_final')
        if outcome and _in_week(outcome.get('finalized_at', ''), week_key):
            finalized += 1
            symbol = (rec.get('outputs') or {}).get('symbol', '?')
            # Find the window + return that gave the verdict
            for wname in ('T1', 'T3', 'T10'):
                slot = lc.get(wname)
                if slot and slot.get('verdict') == outcome.get('verdict'):
                    ret = slot.get('return_pct', 0) or 0
                    entry = {
                        'symbol': symbol,
                        'window': wname,
                        'return_pct': round(ret * 100, 2),
                        'verdict': outcome.get('verdict'),
                    }
                    if outcome.get('verdict') == 'win':
                        top_wins.append(entry)
                    elif outcome.get('verdict') == 'loss':
                        top_losses.append(entry)
                    break

    top_wins.sort(key=lambda x: x['return_pct'], reverse=True)
    top_losses.sort(key=lambda x: x['return_pct'])

    return {
        'new_decisions': new_decisions,
        'total_decisions': len(records),
        't1_filled_this_week': t1_filled,
        't3_filled_this_week': t3_filled,
        't10_filled_this_week': t10_filled,
        'finalized_this_week': finalized,
        'top_wins': top_wins[:3],
        'top_losses': top_losses[:3],
    }


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def format_weekly_report(
    week_key: str,
    week_date: date,
    week_stats: dict,
    chain_breakdown: dict,
) -> str:
    period_start = _date_of_iso_week_start(week_key)
    period_end = period_start + timedelta(days=6)

    def pct(v):
        if v is None:
            return 'N/A'
        return f'{v:.1%}'

    def fmt_rate(bucket):
        wr = bucket.get('win_rate')
        lr = (bucket.get('loss', 0) / bucket.get('total', 1)) if bucket.get('total') else None
        fr = (bucket.get('flat', 0) / bucket.get('total', 1)) if bucket.get('total') else None
        return f"{pct(wr)} | {pct(lr)} | {pct(fr)}"

    rb = chain_breakdown or {}
    rule_b = rb.get('rule_engine', {})
    ai_b = rb.get('ai_bridge', {})
    tier1_b = rb.get('tier1_consensus', {})
    t2_b = rb.get('tier2_rule_overruled_ai', {})

    wins_lines = '\n'.join(
        f"{i+1}. {w['symbol']} — {w['window']} win (+{w['return_pct']}%)"
        for i, w in enumerate(week_stats.get('top_wins', []))
    ) or '（本週無 win 樣本）'

    losses_lines = '\n'.join(
        f"{i+1}. {l['symbol']} — {l['window']} loss ({l['return_pct']}%)"
        for i, l in enumerate(week_stats.get('top_losses', []))
    ) or '（本週無 loss 樣本）'

    lines = [
        f'---',
        f'title: ETF 決策品質週報 {week_key}',
        f'date: {week_date.isoformat()}',
        f'period: {period_start.isoformat()} ~ {period_end.isoformat()}',
        f'---',
        f'',
        f'## 本週摘要',
        f'- 新增決策建議：{week_stats["new_decisions"]} 筆',
        f'- 完成 T1 回填：{week_stats["t1_filled_this_week"]} 筆 / '
        f'T3：{week_stats["t3_filled_this_week"]} 筆 / '
        f'T10：{week_stats["t10_filled_this_week"]} 筆',
        f'- 本週到期完整樣本：{week_stats["finalized_this_week"]} 筆',
        f'',
        f'## 雙鏈勝率（累計）',
        f'| 鏈路 | 樣本數 | 勝率 | 敗率 | 平盤率 |',
        f'|------|--------|------|------|--------|',
        f'| 規則引擎 | {rule_b.get("total", 0)} | {fmt_rate(rule_b)} |',
        f'| AI Bridge | {ai_b.get("total", 0)} | {fmt_rate(ai_b)} |',
        f'| Tier 1 共識 | {tier1_b.get("total", 0)} | {fmt_rate(tier1_b)} |',
        f'| Tier 2 規則強推 | {t2_b.get("total", 0)} | {fmt_rate(t2_b)} |',
        f'',
        f'## 本週最準確標的（Top 3）',
        wins_lines,
        f'',
        f'## 本週最大失誤（Top 3）',
        losses_lines,
    ]

    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def write_weekly_report(content: str, week_key: str, wiki_dir: Path) -> dict:
    """Write content to dated file + latest symlink. Returns {'dated': Path, 'latest': Path}."""
    wiki_dir.mkdir(parents=True, exist_ok=True)

    dated_path = wiki_dir / f'decision-weekly-{week_key}.md'
    latest_path = wiki_dir / 'decision-quality-latest.md'

    dated_path.write_text(content, encoding='utf-8')
    latest_path.write_text(content, encoding='utf-8')

    return {'dated': dated_path, 'latest': latest_path}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    STATE = context.get_state_dir()
    provenance_path = STATE / 'decision_provenance.jsonl'
    quality_report_path = STATE / 'decision_quality_report.json'

    today = datetime.now(TW_TZ).date()
    week_key = iso_week_key(today)

    records = safe_load_jsonl(provenance_path) if provenance_path.exists() else []
    quality_report = safe_load_json(quality_report_path, {})
    chain_breakdown = quality_report.get('chain_breakdown', {})

    week_stats = collect_week_stats(records, today)
    content = format_weekly_report(week_key, today, week_stats, chain_breakdown)
    paths = write_weekly_report(content, week_key, wiki_dir=WIKI_DIR)

    print(f"GENERATE_DECISION_QUALITY_WEEKLY_OK:"
          f"week={week_key} "
          f"new={week_stats['new_decisions']} "
          f"finalized={week_stats['finalized_this_week']} "
          f"dated={paths['dated'].name}")

    # 週報完成後執行門檻校正
    try:
        from auto_calibrate_thresholds import run as calibrate
        calibrate()
    except Exception as exc:
        print(f"[calibrate] 跳過（{exc}）")

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

    return 0


if __name__ == '__main__':
    raise SystemExit(main())