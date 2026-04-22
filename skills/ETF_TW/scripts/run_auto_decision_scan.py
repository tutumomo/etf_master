#!/usr/bin/env python3
from __future__ import annotations
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import sys

from etf_core.state_io import safe_load_json, safe_load_jsonl, atomic_save_json, safe_append_jsonl
from etf_core.state_schema import validate_state_payload
from trading_hours import is_tw_market_open
from provenance_logger import build_provenance_record, append_provenance
from ai_decision_bridge import is_ai_decision_response_stale
from dataclasses import asdict
from sensor_health import check_sensor_health

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')

CONFIG_PATH = STATE / 'auto_trade_config.json'
STATE_PATH = STATE / 'auto_trade_state.json'
WATCHLIST_PATH = STATE / 'watchlist.json'
MARKET_CACHE_PATH = STATE / 'market_cache.json'
PORTFOLIO_PATH = STATE / 'portfolio_snapshot.json'
STRATEGY_PATH = STATE / 'strategy_link.json'
AGENT_SUMMARY_PATH = STATE / 'agent_summary.json'
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
EVENT_CONTEXT_PATH = STATE / 'market_event_context.json'
INTRADAY_TAPE_CONTEXT_PATH = STATE / 'intraday_tape_context.json'
PREVIEW_PATH = STATE / 'auto_preview_candidate.json'
AI_RESPONSE_PATH = STATE / 'ai_decision_response.json'
DECISION_LOG_PATH = STATE / 'decision_log.jsonl'
DECISION_OUTCOMES_PATH = STATE / 'decision_outcomes.jsonl'


# ---------------------------------------------------------------------------
# Dynamic Weight Matrix: weights for different strategies
# ---------------------------------------------------------------------------

STRATEGY_WEIGHTS = {
    '核心累積': {
        'group_base': {'core': 3, 'income': 1.5, 'defensive': 1.5, 'growth': 2, 'smart_beta': 1.5},
        'dimension_weights': {'yield': 0.8, 'momentum': 1.2, 'track_record': 1.0}
    },
    '收益優先': {
        'group_base': {'core': 1.5, 'income': 3, 'defensive': 2, 'growth': 1, 'smart_beta': 1.5},
        'dimension_weights': {'yield': 1.5, 'momentum': 0.8, 'track_record': 1.0}
    },
    '平衡配置': {
        'group_base': {'core': 2, 'income': 2, 'defensive': 2, 'growth': 1.5, 'smart_beta': 1.5},
        'dimension_weights': {'yield': 1.0, 'momentum': 1.0, 'track_record': 1.0}
    },
    '防守保守': {
        'group_base': {'core': 1.5, 'income': 1.5, 'defensive': 3, 'growth': 0.5, 'smart_beta': 1.0},
        'dimension_weights': {'yield': 1.0, 'momentum': 0.5, 'track_record': 1.5}
    }
}

# ---------------------------------------------------------------------------
# Overlay Modifiers: scenario_overlay 對各群組的加/減分修正
# ---------------------------------------------------------------------------

OVERLAY_MODIFIERS = {
    '收益再投資': {'income': +1.0, 'core': +0.5, 'defensive': 0, 'growth': -0.5, 'smart_beta': 0},
    '收益優先':   {'income': +1.5, 'core': 0, 'defensive': +0.5, 'growth': -1.0, 'smart_beta': 0},
    '高波動防守': {'defensive': +2.0, 'core': +0.5, 'income': +0.5, 'growth': -2.0, 'smart_beta': -1.0},
    '減碼保守':   {'defensive': +1.5, 'core': 0, 'income': +0.5, 'growth': -1.5, 'smart_beta': -1.0},
    '積極成長':   {'growth': +2.0, 'core': +0.5, 'smart_beta': +1.0, 'income': -0.5, 'defensive': -1.0},
    '無':         {},  # No overlay modifier
}

# ---------------------------------------------------------------------------
# Buy Threshold By Risk Temperature: dynamic threshold replacing hardcoded 4
# ---------------------------------------------------------------------------

BUY_THRESHOLD_BY_RISK = {
    'low':      3.5,   # 低風險市場：放寬門檻，鼓勵建倉
    'normal':   4.0,   # 一般市場：標準門檻
    'elevated': 5.0,   # 高風險市場：提高門檻，保守操作
    'high':     6.0,   # 極高風險：非常保守
}


# ---------------------------------------------------------------------------
# Consensus Arbitration: resolve conflicts between Rule Engine & AI Bridge
# ---------------------------------------------------------------------------

def _adjust_confidence(base: str, rule_aligned: bool | None, ai_aligned: bool | None) -> str:
    """策略對齊信心調整：雙鏈對齊升級，任一不對齊降級。"""
    both_aligned = rule_aligned is True and ai_aligned is True
    either_misaligned = rule_aligned is False or ai_aligned is False
    if both_aligned and base == 'medium':
        return 'high'
    if either_misaligned and base == 'high':
        return 'medium'
    if either_misaligned and base == 'medium':
        return 'low'
    return base


def resolve_consensus(
    rule_engine_action: str | None,
    ai_bridge_action: str | None,
    rule_engine_symbol: str | None,
    ai_bridge_symbol: str | None,
    rule_score: int | None = None,
    rule_strategy_aligned: bool | None = None,   # NEW: from 06-01 candidate result
    ai_strategy_aligned: bool | None = None,      # NEW: from 06-02 candidate result
) -> dict:
    """
    Three-tier arbitration:
      Tier 1: Both agree on symbol + direction -> high confidence, execute
      Tier 2: Disagree on symbol or direction -> rule engine has veto power
      Tier 3: Opposite directions on same symbol -> LOCK, wait for human

    Returns consensus dict:
      {
        "rule_engine": <action or None>,
        "ai_bridge": <action or None>,
        "rule_engine_symbol": <symbol or None>,
        "ai_bridge_symbol": <symbol or None>,
        "resolved": <"buy"|"sell"|"hold"|"locked">,
        "confidence_level": <"high"|"medium"|"low">,
        "conflict": <bool>,
        "conflict_detail": <str or None>,
        "tier": <1|2|3>,
        "strategy_alignment_signal": {"rule": <bool|None>, "ai": <bool|None>},
      }
    """
    rule_action = (rule_engine_action or 'hold').lower()
    ai_action = (ai_bridge_action or 'hold').lower()
    rule_sym = (rule_engine_symbol or '').strip()
    ai_sym = (ai_bridge_symbol or '').strip()

    # Normalize AI Bridge action keywords to buy/sell/hold
    ai_normalized = ai_action
    for prefix in ('preview_', 'suggest_', 'recommend_'):
        if ai_normalized.startswith(prefix):
            ai_normalized = ai_normalized[len(prefix):]
    if ai_normalized in ('buy', 'long', 'add', 'accumulate'):
        ai_normalized = 'buy'
    elif ai_normalized in ('sell', 'short', 'reduce', 'trim', 'close'):
        ai_normalized = 'sell'
    else:
        ai_normalized = 'hold'

    rule_side = rule_action if rule_action in ('buy', 'sell') else 'hold'

    _alignment_signal = {'rule': rule_strategy_aligned, 'ai': ai_strategy_aligned}

    # --- Tier 1: Full agreement ---
    if rule_side != 'hold' and ai_normalized != 'hold' and rule_sym and ai_sym and rule_sym == ai_sym and rule_side == ai_normalized:
        return {
            'rule_engine': rule_side,
            'ai_bridge': ai_normalized,
            'rule_engine_symbol': rule_sym,
            'ai_bridge_symbol': ai_sym,
            'resolved': rule_side,
            'confidence_level': _adjust_confidence('high', rule_strategy_aligned, ai_strategy_aligned),
            'conflict': False,
            'conflict_detail': None,
            'tier': 1,
            'strategy_alignment_signal': _alignment_signal,
        }

    # --- Tier 3: Opposite directions on same symbol ---
    if rule_sym and ai_sym and rule_sym == ai_sym and rule_side != 'hold' and ai_normalized != 'hold' and rule_side != ai_normalized:
        return {
            'rule_engine': rule_side,
            'ai_bridge': ai_normalized,
            'rule_engine_symbol': rule_sym,
            'ai_bridge_symbol': ai_sym,
            'resolved': 'locked',
            'confidence_level': _adjust_confidence('low', rule_strategy_aligned, ai_strategy_aligned),
            'conflict': True,
            'conflict_detail': f'方向衝突：規則引擎={rule_side} vs AI Bridge={ai_normalized}，標的={rule_sym}',
            'tier': 3,
            'strategy_alignment_signal': _alignment_signal,
        }

    # --- Tier 2: Disagreement (different symbol, or one says hold) ---
    # Rule engine has veto power: AI can boost but not override

    # Rule engine is actionable, AI disagrees or targets different symbol
    if rule_side != 'hold' and rule_sym:
        if ai_normalized == 'hold':
            # AI says hold -> downgrade confidence but don't block
            return {
                'rule_engine': rule_side,
                'ai_bridge': 'hold',
                'rule_engine_symbol': rule_sym,
                'ai_bridge_symbol': ai_sym or None,
                'resolved': rule_side,
                'confidence_level': _adjust_confidence('low', rule_strategy_aligned, ai_strategy_aligned),
                'conflict': True,
                'conflict_detail': f'AI Bridge 建議 hold，規則引擎建議 {rule_side} {rule_sym}，降級執行',
                'tier': 2,
                'strategy_alignment_signal': _alignment_signal,
            }
        if ai_sym and ai_sym != rule_sym:
            # Different symbols -> rule engine wins
            return {
                'rule_engine': rule_side,
                'ai_bridge': ai_normalized,
                'rule_engine_symbol': rule_sym,
                'ai_bridge_symbol': ai_sym,
                'resolved': rule_side,
                'confidence_level': _adjust_confidence('medium', rule_strategy_aligned, ai_strategy_aligned),
                'conflict': True,
                'conflict_detail': f'標的不同：規則引擎={rule_sym} vs AI Bridge={ai_sym}，規則引擎優先',
                'tier': 2,
                'strategy_alignment_signal': _alignment_signal,
            }
        if rule_side == ai_normalized and rule_sym == ai_sym:
            # Same direction same symbol (already handled by Tier 1, but safe fallback)
            return {
                'rule_engine': rule_side,
                'ai_bridge': ai_normalized,
                'rule_engine_symbol': rule_sym,
                'ai_bridge_symbol': ai_sym,
                'resolved': rule_side,
                'confidence_level': _adjust_confidence('high', rule_strategy_aligned, ai_strategy_aligned),
                'conflict': False,
                'conflict_detail': None,
                'tier': 1,
                'strategy_alignment_signal': _alignment_signal,
            }
        # Same symbol, same direction but Tier 1 didn't catch -> fallback agree
        if rule_sym == ai_sym and rule_side == ai_normalized:
            return {
                'rule_engine': rule_side,
                'ai_bridge': ai_normalized,
                'rule_engine_symbol': rule_sym,
                'ai_bridge_symbol': ai_sym,
                'resolved': rule_side,
                'confidence_level': _adjust_confidence('high', rule_strategy_aligned, ai_strategy_aligned),
                'conflict': False,
                'conflict_detail': None,
                'tier': 1,
                'strategy_alignment_signal': _alignment_signal,
            }

    # Rule engine says hold, AI wants to act -> veto, AI cannot override
    if rule_side == 'hold' and ai_normalized != 'hold' and ai_sym:
        return {
            'rule_engine': 'hold',
            'ai_bridge': ai_normalized,
            'rule_engine_symbol': rule_sym or None,
            'ai_bridge_symbol': ai_sym,
            'resolved': 'hold',
            'confidence_level': _adjust_confidence('low', rule_strategy_aligned, ai_strategy_aligned),
            'conflict': True,
            'conflict_detail': f'規則引擎否決：AI Bridge 建議 {ai_normalized} {ai_sym}，但規則引擎未達門檻',
            'tier': 2,
            'strategy_alignment_signal': _alignment_signal,
        }

    # Both say hold
    return {
        'rule_engine': 'hold',
        'ai_bridge': ai_normalized,
        'rule_engine_symbol': rule_sym or None,
        'ai_bridge_symbol': ai_sym or None,
        'resolved': 'hold',
        'confidence_level': _adjust_confidence('medium', rule_strategy_aligned, ai_strategy_aligned),
        'conflict': False,
        'conflict_detail': None,
        'tier': 1,
        'strategy_alignment_signal': _alignment_signal,
    }




def _session_dedup_key(result: dict) -> str | None:
    """Build a dedup key: same date + same symbol + same action = same session decision.
    Hold decisions are NOT deduplicated — each hold carries unique market context."""
    now = datetime.now(TW_TZ)
    date_key = now.strftime('%Y-%m-%d')
    cands = result.get('top_candidates', [])
    symbol = cands[0]['symbol'] if cands else None
    action = result.get('action', 'hold')
    # Hold decisions: skip dedup entirely (each scan's market context is different)
    if action == 'hold' or not symbol:
        return None
    return f"{date_key}|{symbol}|{action}"


def _is_duplicate_session(dedup_key: str, decision_log_path: Path) -> bool:
    """Check if this session key already exists in today's decision_log."""
    # dedup_key format: "YYYY-MM-DD|SYMBOL|ACTION"
    rows = safe_load_jsonl(decision_log_path)
    for row in rows:
        # Use explicit 'date' and 'symbol' fields if available, otherwise fallback
        row_date = row.get('date') or (row.get('scanned_at', '')[:10])
        cands = row.get('top_candidates', [])
        sym = row.get('symbol') or (cands[0]['symbol'] if cands else None)
        action = row.get('action', 'hold')
        
        if not row_date or not sym: continue
        
        row_key = f"{row_date}|{sym}|{action}"
        if row_key == dedup_key:
            return True
    return False


def _load_market_intelligence() -> dict:
    """Load market_intelligence.json for momentum/sharpe/return data."""
    intel_path = STATE / 'market_intelligence.json'
    try:
        data = safe_load_json(intel_path, {'intelligence': {}})
        return data.get('intelligence', {})
    except Exception:
        return {}


def _score_yield(symbol: str, wl_yield: float | None, intel: dict) -> tuple[float, list[str]]:
    """TOMO 原則 1：價值被低估 → 殖利率越高越好。

    Sources (priority): watchlist yield_pct > shioaji data > 0
    """
    score = 0.0
    reasons = []

    # watchlist yield is authoritative (set by operator or future data pipeline)
    if isinstance(wl_yield, (int, float)) and wl_yield > 0:
        if wl_yield >= 5.0:
            score += 2
            reasons.append(f'殖利率 {wl_yield:.1f}% 偏高，具收益吸引力')
        elif wl_yield >= 3.5:
            score += 1
            reasons.append(f'殖利率 {wl_yield:.1f}% 中等，收益尚可')
        # Below 3.5%: 殖利率偏低，不加分
    else:
        # Fallback: no yield data available → no bonus, no penalty
        reasons.append('殖利率資料待補')

    return score, reasons


def _score_momentum(symbol: str, intel: dict) -> tuple[float, list[str]]:
    """TOMO 原則 2：前景看好 → 動能為正且穩定。

    Uses momentum_20d from market_intelligence.
    Also cross-checks RSI (overbought = 看好但過熱) and MACD histogram direction.
    """
    score = 0.0
    reasons = []
    m = intel.get(symbol, {})
    mom = m.get('momentum_20d')
    rsi = m.get('rsi')
    macd = m.get('macd', 0)
    macd_sig = m.get('macd_signal', 0)

    if isinstance(mom, (int, float)):
        if mom > 5:
            score += 2
            reasons.append(f'20日動能 +{mom:.1f}%，趨勢強勁')
        elif mom > 1:
            score += 1
            reasons.append(f'20日動能 +{mom:.1f}%，趨勢偏多')
        elif mom < -5:
            score -= 1
            reasons.append(f'20日動能 {mom:.1f}%，趨勢偏弱')
        elif mom < -1:
            # Slight negative: not penalized heavily, just no bonus
            reasons.append(f'20日動能 {mom:.1f}%，動能微降')
    else:
        reasons.append('動能資料待補')

    # RSI cross-check: momentum positive but RSI > 75 = 過熱
    if isinstance(rsi, (int, float)) and rsi > 75:
        score -= 1
        reasons.append(f'RSI {rsi:.0f} 偏高，動能雖好但過熱需留意')

    # MACD direction confirmation
    if isinstance(macd, (int, float)) and isinstance(macd_sig, (int, float)):
        hist = macd - macd_sig
        if hist > 0 and (isinstance(mom, (int, float)) and mom > 0):
            score += 0.5  # MACD confirms momentum
            reasons.append('MACD 多方排列，動能方向一致')

    return score, reasons


def _score_track_record(symbol: str, intel: dict) -> tuple[float, list[str]]:
    """TOMO 原則 3：過往紀錄良好 → 夏普值高、1年報酬正。

    Uses sharpe_30d and return_1y from market_intelligence.
    """
    score = 0.0
    reasons = []
    m = intel.get(symbol, {})
    sharpe = m.get('sharpe_30d')
    ret_1y = m.get('return_1y')

    # Sharpe ratio
    if isinstance(sharpe, (int, float)):
        if sharpe > 2.0:
            score += 2
            reasons.append(f'夏普值 {sharpe:.1f} 優異，風險調整後報酬佳')
        elif sharpe > 0.5:
            score += 1
            reasons.append(f'夏普值 {sharpe:.1f} 尚可')
        elif sharpe < -0.5:
            score -= 1
            reasons.append(f'夏普值 {sharpe:.1f} 偏低，近期風險調整報酬不佳')
    else:
        reasons.append('夏普值資料待補')

    # 1-year return
    if isinstance(ret_1y, (int, float)):
        if ret_1y > 20:
            score += 1
            reasons.append(f'1年報酬 +{ret_1y:.0f}%，過往紀錄良好')
        elif ret_1y < -10:
            score -= 1
            reasons.append(f'1年報酬 {ret_1y:.0f}%，過往表現偏弱')
    else:
        reasons.append('1年報酬資料待補')

    return score, reasons


def decide_action(strategy: dict, watchlist: dict, market_cache: dict, portfolio: dict, market_context: dict, event_context: dict, tape_context: dict) -> dict:
    quotes = market_cache.get('quotes', {})
    holdings = {h.get('symbol'): h for h in portfolio.get('holdings', [])}
    items = watchlist.get('items', [])
    anomalies = []
    candidates = []
    base_strategy = strategy.get('base_strategy') or '平衡配置'
    scenario_overlay = strategy.get('scenario_overlay') or '無'
    risk_temperature = market_context.get('risk_temperature', 'normal')
    core_tilt = market_context.get('core_tilt', 'neutral')
    income_tilt = market_context.get('income_tilt', 'neutral')
    defensive_tilt = market_context.get('defensive_tilt', 'neutral')
    geo_political_risk = event_context.get('geo_political_risk', 'unknown')
    global_risk_level = event_context.get('global_risk_level', 'unknown')
    tape_signals = {row.get('symbol'): row for row in tape_context.get('watchlist_signals', [])}

    # Load market intelligence for TOMO 三原則維度
    intel = _load_market_intelligence()

    # Get strategy weights
    weights = STRATEGY_WEIGHTS.get(base_strategy, STRATEGY_WEIGHTS['平衡配置'])
    group_base = weights['group_base']
    dim_weights = weights['dimension_weights']

    for item in items:
        symbol = item.get('symbol')
        group = item.get('group') or 'other'
        quote = quotes.get(symbol) or {}
        price = float(quote.get('current_price') or 0)
        if price <= 0:
            # 區分「尚未更新」與「真正無報價」
            updated_at_str = quote.get('updated_at', '')
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if datetime.now(updated_at.tzinfo) - updated_at < timedelta(hours=2):
                        anomalies.append(f'{symbol} 報價更新中（最後更新 {updated_at_str[:16]}）')
                    else:
                        anomalies.append(f'{symbol} 報價過期（最後更新 {updated_at_str[:16]}）')
                except Exception:
                    anomalies.append(f'{symbol} 無有效報價')
            else:
                anomalies.append(f'{symbol} 尚無報價資料')
            continue

        holding_qty = float((holdings.get(symbol) or {}).get('quantity') or 0)
        score = 0.0
        reasons = []
        risk_notes = []

        # === 基礎分（群組歸屬）===
        score += group_base.get(group, 1)
        reasons.append(f'屬於{group}配置池（基於 {base_strategy} 策略，基礎分 {group_base.get(group, 1)}）')

        # 群組傾向加分
        if group == 'core' and core_tilt == 'high':
            score += 1
            reasons.append('市場情勢偏向核心配置')
        elif group == 'income' and income_tilt == 'high':
            score += 1
            reasons.append('市場情勢偏向收益配置')
        elif group == 'defensive' and defensive_tilt == 'high':
            score += 1
            reasons.append('市場情勢偏向防守配置')

        # === 持倉調整 ===
        group_size = sum(1 for i in items if (i.get('group') or 'other') == group)
        not_held_bonus = 1.0  # reduced from +2 (教訓20)
        if holding_qty <= 0:
            if group_size > 1:
                not_held_bonus = round(1 / (group_size ** 0.5), 2) or 0.5
            score += not_held_bonus
            reasons.append(f'未持有可新增（同群 {group_size} 檔競爭，加分 {not_held_bonus}）')
        else:
            score -= 1
            risk_notes.append('已有持倉，避免重複加碼過快')

        # === 盤感層 ===
        tape_signal = tape_signals.get(symbol, {})
        if tape_signal.get('intraday_position') == 'near-low':
            score += 1
            reasons.append('接近日內低區，可列入逢低觀察')
        if tape_signal.get('rebound_watch'):
            score += 1
            reasons.append('盤感層顯示可列入反彈觀察')
        if tape_signal.get('falling_knife_risk'):
            score -= 2
            risk_notes.append('盤感層顯示接刀風險偏高')

        # === 風險環境 ===
        if risk_temperature == 'elevated':
            score -= 1
            risk_notes.append('市場風險溫度偏高')
            if group != 'defensive':
                score -= 1
                risk_notes.append('非防守型在高風險情境需更保守')

        if global_risk_level == 'elevated' or geo_political_risk == 'high':
            score -= 1
            risk_notes.append('外部宏觀/地緣政治風險偏高')
            if group == 'defensive':
                score += 1
                reasons.append('外部風險升高，防守型相對受益')

        # === 策略對齊（含 overlay 修正）===
        strategy_aligned = False
        if base_strategy == '平衡配置' and group in {'core', 'income'}:
            score += 1
            reasons.append('符合平衡配置主要候選')
            strategy_aligned = True
        if base_strategy == '核心累積' and group == 'core':
            strategy_aligned = True
        if base_strategy == '收益優先' and group == 'income':
            strategy_aligned = True
        if base_strategy == '防守保守' and group == 'defensive':
            strategy_aligned = True

        # Apply scenario_overlay modifiers from OVERLAY_MODIFIERS table
        overlay_mod = OVERLAY_MODIFIERS.get(scenario_overlay, {})
        overlay_delta = overlay_mod.get(group, 0)
        if overlay_delta != 0:
            score += overlay_delta
            if overlay_delta > 0:
                reasons.append(f'情境疊加「{scenario_overlay}」加分 +{overlay_delta}（群組 {group}）')
                strategy_aligned = True
            else:
                reasons.append(f'情境疊加「{scenario_overlay}」扣分 {overlay_delta}（群組 {group}）')
        elif scenario_overlay in {'收益再投資', '收益優先'} and group == 'income':
            # fallback for groups not in overlay dict
            score += 1
            reasons.append('符合收益傾向情境')
            strategy_aligned = True
        if scenario_overlay in {'高波動防守', '減碼保守'} and group == 'defensive' and overlay_delta == 0:
            score += 1
            reasons.append('符合防守情境')
            strategy_aligned = True
        if market_context.get('market_regime') == 'cautious' and group == 'defensive':
            score += 1
            reasons.append('市場 regime 偏保守，防守型優先度提高')

        # === TOMO 買入三原則（量化維度）===
        wl_yield = item.get('yield_pct')
        if isinstance(wl_yield, str):
            try:
                wl_yield = float(wl_yield)
            except (ValueError, TypeError):
                wl_yield = None

        yield_score, yield_reasons = _score_yield(symbol, wl_yield, intel)
        momentum_score, momentum_reasons = _score_momentum(symbol, intel)
        track_score, track_reasons = _score_track_record(symbol, intel)

        # Apply strategy weights to dimensions
        weighted_yield = yield_score * dim_weights.get('yield', 1.0)
        weighted_momentum = momentum_score * dim_weights.get('momentum', 1.0)
        weighted_track = track_score * dim_weights.get('track_record', 1.0)

        score += weighted_yield + weighted_momentum + weighted_track
        reasons.extend(yield_reasons + momentum_reasons + track_reasons)

        candidates.append({
            'symbol': symbol,
            'side': 'buy' if holding_qty <= 0 else 'hold',
            'price': price,
            'group': group,
            'score': round(score, 2),
            'reasons': reasons,
            'risk_notes': risk_notes,
            'holding_qty': holding_qty,
            'strategy_aligned': strategy_aligned,
            # 新維度明細（方便 dashboard 展示）
            'dimension_scores': {
                'yield': round(weighted_yield, 2),
                'momentum': round(weighted_momentum, 2),
                'track_record': round(weighted_track, 2),
            },
        })

    candidates.sort(key=lambda x: x['score'], reverse=True)
    buy_threshold = BUY_THRESHOLD_BY_RISK.get(risk_temperature, BUY_THRESHOLD_BY_RISK['normal'])
    actionable = next((c for c in candidates if c['side'] == 'buy' and c['score'] >= buy_threshold), None)

    if actionable:
        dims = actionable.get('dimension_scores', {})
        dim_desc = f"（殖利率{dims.get('yield',0):+.1f} 動能{dims.get('momentum',0):+.1f} 紀錄{dims.get('track_record',0):+.1f}）"
        summary = f"建議優先關注 {actionable['symbol']}，分數 {actionable['score']:.1f}{dim_desc}，可建立買進 preview。"
        action = 'buy-preview'
        confidence = '中高'
    else:
        summary = '目前以觀望為主，暫無安全的新增 preview 候選。'
        action = 'hold'
        confidence = '中'

    if anomalies:
        summary += ' 異常：' + '；'.join(anomalies)

    return {
        'action': action,
        'summary': summary,
        'candidate': actionable,
        'uncertainty': confidence,
        'base_strategy': base_strategy,
        'scenario_overlay': scenario_overlay,
        'anomalies': anomalies,
        'top_candidates': candidates[:3],
    }


def test_consensus_logic() -> int:
    """Test various consensus scenarios."""
    scenarios = [
        # (rule_act, ai_act, rule_sym, ai_sym, expected_tier, expected_resolved)
        ('buy', 'buy', '0050', '0050', 1, 'buy'),        # Agree
        ('buy', 'sell', '0050', '0050', 3, 'locked'),     # Opposite
        ('buy', 'hold', '0050', '0050', 2, 'buy'),        # AI says hold, rule wins
        ('hold', 'buy', '0050', '0050', 2, 'hold'),       # Rule says hold, rule wins (veto)
        ('buy', 'buy', '0050', '006208', 2, 'buy'),      # Different symbols, rule wins
    ]
    
    print("--- Running Consensus Logic Tests ---")
    all_pass = True
    for ra, aa, rs, ais, et, er in scenarios:
        res = resolve_consensus(ra, aa, rs, ais)
        passed = res['tier'] == et and res['resolved'] == er
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] Rule:{ra}/{rs} + AI:{aa}/{ais} -> Tier {res['tier']} Resolved:{res['resolved']}")
        if not passed:
            print(f"      Expected: Tier {et} Resolved: {er}")
            all_pass = False
            
    if all_pass:
        print("ALL_CONSENSUS_TESTS_PASSED")
        return 0
    else:
        print("SOME_CONSENSUS_TESTS_FAILED")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-consensus', action='store_true', help='測試共識仲裁邏輯')
    args = parser.parse_args(argv)

    if args.test_consensus:
        return test_consensus_logic()

    now = datetime.now(TW_TZ)
    config = validate_state_payload('auto_trade_config', safe_load_json(CONFIG_PATH, {}), {
        'enabled': False, 'frequency_minutes': 30, 'trading_hours_only': True
    })
    state = validate_state_payload('auto_trade_state', safe_load_json(STATE_PATH, {}), {
        'enabled': False, 'last_scan_at': None, 'last_decision_summary': None
    })
    strategy = safe_load_json(STRATEGY_PATH, {})
    watchlist = safe_load_json(WATCHLIST_PATH, {'items': []})
    market_cache = safe_load_json(MARKET_CACHE_PATH, {'quotes': {}})
    portfolio = safe_load_json(PORTFOLIO_PATH, {'holdings': []})
    agent_summary = safe_load_json(AGENT_SUMMARY_PATH, {})
    market_context = validate_state_payload('market_context_taiwan', safe_load_json(MARKET_CONTEXT_PATH, {
        'market_regime': 'unknown',
        'risk_temperature': 'normal',
        'core_tilt': 'neutral',
        'income_tilt': 'neutral',
        'defensive_tilt': 'neutral',
        'context_summary': '尚無台灣市場情勢摘要',
    }), {
        'market_regime': 'unknown', 'risk_temperature': 'normal', 'context_summary': '尚無台灣市場情勢摘要'
    })
    event_context = validate_state_payload('market_event_context', safe_load_json(EVENT_CONTEXT_PATH, {
        'global_risk_level': 'unknown',
        'geo_political_risk': 'unknown',
        'energy_risk': 'unknown',
        'summary': '尚無外部事件情境摘要',
        'event_regime': 'unknown'
    }), {
        'event_regime': 'unknown', 'global_risk_level': 'unknown', 'summary': '尚無外部事件情境摘要'
    })
    tape_context = safe_load_json(INTRADAY_TAPE_CONTEXT_PATH, {
        'market_bias': 'unknown',
        'tape_summary': '尚無盤感輔助層摘要',
        'watchlist_signals': [],
    })

    # Read event flag to annotate provenance records
    _event_flag = safe_load_json(STATE / 'major_event_flag.json', {})
    _event_triggered = (
        _event_flag.get('triggered', False) and
        _event_flag.get('level', 'none') in ('L2', 'L3') and
        bool(_event_flag.get('should_notify'))
    )
    _event_level = _event_flag.get('level', 'none') if _event_triggered else None

    enabled = bool(config.get('enabled', False))
    market_open = is_tw_market_open(now)
    state.update({
        'enabled': enabled,
        'frequency_minutes': int(config.get('frequency_minutes', 30) or 30),
        'trading_hours_only': bool(config.get('trading_hours_only', True)),
        'market_session_open': market_open,
        'updated_at': now.isoformat(),
        'source': 'run_auto_decision_scan',
    })

    if not enabled:
        state['lock_reason'] = '功能尚未啟用'
        atomic_save_json(STATE_PATH, state)
        print('AUTO_DECISION_SCAN_OK:DISABLED')
        return 0

    if config.get('trading_hours_only', True) and not market_open:
        state['lock_reason'] = '非交易時段，已自動停用'
        atomic_save_json(STATE_PATH, state)
        print('AUTO_DECISION_SCAN_OK:LOCKED')
        return 0

    # ── 感測器健康檢查 ──────────────────────────────────────────────────────
    health = check_sensor_health(STATE)
    try:
        atomic_save_json(STATE / 'sensor_health.json', asdict(health))
    except Exception as _e:
        print(f'[sensor_health] sensor_health.json 寫入失敗（{_e}），繼續執行')

    if not health.healthy:
        state['lock_reason'] = f'關鍵感測器失效：{", ".join(health.critical_failures)}'
        atomic_save_json(STATE_PATH, state)
        print(f'AUTO_DECISION_SCAN_CRITICAL_SENSOR_FAIL:{",".join(health.critical_failures)}')
        return 1

    if health.warning_prefix:
        market_context = dict(market_context)
        market_context['context_summary'] = (
            health.warning_prefix + str(market_context.get('context_summary') or '')
        )
    # ───────────────────────────────────────────────────────────────────────

    result = decide_action(strategy, watchlist, market_cache, portfolio, market_context, event_context, tape_context)
    candidate = result.get('candidate')
    preview_summary = None

    # --- Consensus Arbitration: cross-check with AI Bridge ---
    ai_response = safe_load_json(AI_RESPONSE_PATH, {})
    ai_stale = is_ai_decision_response_stale(ai_response) if ai_response else True
    ai_action = None
    ai_symbol = None
    if not ai_stale:
        ai_action = (ai_response.get('decision') or {}).get('action')
        ai_symbol = (ai_response.get('candidate') or {}).get('symbol')
    rule_action = 'buy' if candidate and candidate.get('side') == 'buy' else 'hold'
    rule_symbol = candidate.get('symbol') if candidate else None
    consensus = resolve_consensus(
        rule_engine_action=rule_action,
        ai_bridge_action=ai_action,
        rule_engine_symbol=rule_symbol,
        ai_bridge_symbol=ai_symbol,
        rule_score=candidate.get('score') if candidate else None,
    )
    print(f"[CONSENSUS] Tier {consensus['tier']} | resolved={consensus['resolved']} | confidence={consensus['confidence_level']} | conflict={consensus['conflict']}")
    if consensus['conflict_detail']:
        print(f"[CONSENSUS] {consensus['conflict_detail']}")

    if candidate:
        preview_payload = {
            'symbol': candidate['symbol'],
            'side': candidate['side'],
            'reference_price': candidate['price'],
            'quantity': 100,
            'order_type': 'market',
            'mode': 'preview-only',
            'not_submitted': True,
            'group': candidate.get('group'),
            'score': candidate.get('score'),
            'reason': '；'.join(candidate.get('reasons', [])) or f"{candidate['symbol']} 符合目前策略，可列為 preview 候選",
            'risk_note': '；'.join(candidate.get('risk_notes', [])) or '仍需先做 validate / preview，非自動下單',
            'uncertainty': result['uncertainty'],
            'strategy_alignment': f"{result['base_strategy']} / {result['scenario_overlay']}",
            'generated_at': now.isoformat(),
            'consensus': consensus,
        }
        # Tier 3 (locked) or Tier 2 with low confidence: mark as blocked
        if consensus['resolved'] == 'locked':
            preview_payload['mode'] = 'preview-locked'
            preview_payload['risk_note'] = (preview_payload.get('risk_note', '') + '；⚠️ 仲裁鎖定：方向衝突，需人工確認').lstrip('；')
        elif consensus['confidence_level'] == 'low':
            preview_payload['mode'] = 'preview-low-confidence'
        atomic_save_json(PREVIEW_PATH, preview_payload)
        preview_summary = f"已建立 {candidate['symbol']} 的 preview 候選（未送單）；信心 {result['uncertainty']}；分數 {candidate.get('score')}；仲裁 Tier {consensus['tier']} {consensus['resolved']}"
    state['lock_reason'] = None
    state['last_scan_at'] = now.isoformat()
    state['last_decision_summary'] = result['summary']
    state['last_preview_summary'] = preview_summary or '本次未建立 preview 候選'
    state['last_action'] = result['action']
    # P2: 狀態分離 - 確保 auto_trade_state 不會覆蓋 auto_submit_state
    # 此處只更新掃描狀態，不觸碰 live_submit_allowed 等送單控制欄位
    atomic_save_json(STATE_PATH, state)

    # P2: 明確記錄 - 此掃描不影響送單狀態
    print(f"[STATE] auto_trade_state 已更新，auto_submit_state 不受影響")

    # --- Session dedup: skip if same date + symbol + action already recorded ---
    dedup_key = _session_dedup_key(result)
    if dedup_key and _is_duplicate_session(dedup_key, DECISION_LOG_PATH):
        print(f"DEDUP_SKIP: {dedup_key} 已於今日記錄，跳過重複 append")
        print('AUTO_DECISION_SCAN_OK:DEDUP')
        return 0

    decision_id = f"decision-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    evaluation_window = '1-3 trading days' if result['action'] == 'buy-preview' else 'short-medium'
    safe_append_jsonl(DECISION_LOG_PATH, {
        'decision_id': decision_id,
        'date': now.strftime('%Y-%m-%d'),
        'symbol': (candidate or {}).get('symbol') or (result.get('top_candidates', [{}])[0].get('symbol')),
        'scanned_at': now.isoformat(),
        'summary': result['summary'],
        'action': result['action'],
        'preview_summary': state['last_preview_summary'],
        'uncertainty': result['uncertainty'],
        'anomalies': result.get('anomalies', []),
        'top_candidates': result.get('top_candidates', []),
        'evaluation_window': evaluation_window,
        'outcome_status': 'pending',
        'strategy': {
            'base_strategy': result['base_strategy'],
            'scenario_overlay': result['scenario_overlay'],
        },
        'portfolio_brief': agent_summary.get('portfolio_brief'),
        'market_context': market_context,
        'tape_context': {
            'market_bias': tape_context.get('market_bias'),
            'tape_summary': tape_context.get('tape_summary'),
            'candidate_signal': next((row for row in tape_context.get('watchlist_signals', []) if row.get('symbol') == (candidate or {}).get('symbol')), None),
        },
    })
    safe_append_jsonl(DECISION_OUTCOMES_PATH, {
        'decision_id': decision_id,
        'created_at': now.isoformat(),
        'evaluation_window': evaluation_window,
        'action': result['action'],
        'symbol': (candidate or {}).get('symbol'),
        'outcome_status': 'pending',
        'outcome_note': '待後續 review / market outcome 回填',
        'strategy': {
            'base_strategy': result['base_strategy'],
            'scenario_overlay': result['scenario_overlay'],
        }
    })

    # --- Provenance: record every scan decision ---
    provenance_path = STATE / 'decision_provenance.jsonl'
    try:
        request_payload = {
            'request_id': decision_id,
            'inputs': {
                'strategy': strategy,
                'positions': portfolio,
                'market_context_taiwan': market_context,
                'market_event_context': event_context,
                'intraday_tape_context': tape_context,
                'portfolio_snapshot': portfolio,
                'market_cache': market_cache,
                'orders_open': {},
            },
        }
        response_payload = {
            'request_id': decision_id,
            'decision': {
                'summary': result['summary'],
                'action': result['action'],
                'confidence': result['uncertainty'],
            },
            'candidate': {
                'symbol': (candidate or {}).get('symbol'),
                'reference_price': (candidate or {}).get('price'),
                'quantity': 100,
            },
        }
        scan_result = result
        # Build chain_sources from consensus dict for dual-chain stats
        ai_bridge_reasoning = ai_response.get('decision', {}).get('summary') if consensus['conflict'] else None
        chain_sources_payload = {
            'rule_engine_action': consensus.get('rule_engine'),
            'rule_engine_symbol': consensus.get('rule_engine_symbol'),
            'ai_bridge_action': consensus.get('ai_bridge'),
            'ai_bridge_symbol': consensus.get('ai_bridge_symbol'),
            'consensus_tier': consensus.get('tier'),
            'consensus_resolved': consensus.get('resolved'),
            'strategy_aligned_rule': (consensus.get('strategy_alignment_signal') or {}).get('rule'),
            'strategy_aligned_ai': (consensus.get('strategy_alignment_signal') or {}).get('ai'),
            'conflict_detail': consensus['conflict_detail'],
            'ai_bridge_reasoning': ai_bridge_reasoning,
            'event_triggered': _event_triggered,
            'event_level': _event_level,
        }
        record = build_provenance_record(
            request_payload=request_payload,
            response_payload=response_payload,
            scan_result=scan_result,
            source='run_auto_decision_scan',
            chain_sources=chain_sources_payload,
        )
        append_provenance(provenance_path, record)
    except Exception as e:
        import warnings
        warnings.warn(f"[provenance] Failed to append provenance record: {e}")

    print('AUTO_DECISION_SCAN_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
