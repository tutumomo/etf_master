#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from scripts.ai_decision_bridge import build_agent_consumed_response_payload


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _resolve_entity_wiki_text(symbol: str, request_payload: dict, limit: int = 800) -> str:
    """優先吃 request 內的 wiki_context，其次 fallback 到 profile/instance wiki 檔案。"""
    if not symbol:
        return ''

    req_entities = ((request_payload.get('wiki_context') or {}).get('entities') or {})
    if symbol in req_entities and req_entities.get(symbol):
        return str(req_entities[symbol])[:limit]

    dirs = [
        ROOT.parent.parent / 'wiki' / 'entities',
        ROOT / 'instances' / 'etf_master' / 'wiki' / 'entities',
        ROOT / 'instances' / 'etf_master' / 'llm-wiki' / 'etf',
    ]
    for d in dirs:
        if not d.exists():
            continue
        exact = d / f'{symbol}.md'
        if exact.exists():
            try:
                return exact.read_text(encoding='utf-8')[:limit]
            except Exception:
                pass
        for p in sorted(d.glob(f'{symbol}-*.md')):
            try:
                txt = p.read_text(encoding='utf-8')
                if txt:
                    return txt[:limit]
            except Exception:
                continue
    return ''


def _build_agent_reasoning(request_payload: dict, quality_state: dict | None = None) -> tuple[dict, dict, str, str, str]:
    inputs = request_payload.get('inputs', {})
    strategy = inputs.get('strategy') or {}
    market_context = inputs.get('market_context_taiwan') or {}
    event_context = inputs.get('market_event_context') or {}
    intelligence = (inputs.get('market_intelligence') or {}).get('intelligence') or {}
    decision_memory_context = inputs.get('decision_memory_context') or {}
    tape_context = inputs.get('intraday_tape_context') or {}
    worldmonitor_context = inputs.get('worldmonitor_context') or {}
    wiki_context = request_payload.get('wiki_context') or {}
    market_view_wiki = str(wiki_context.get('market_view') or '')
    risk_signal_wiki = str(wiki_context.get('risk_signal') or '')
    learned_rules_draft = str(wiki_context.get('learned_rules_draft') or '')

    risk_temperature = market_context.get('risk_temperature', 'unknown')
    market_regime = market_context.get('market_regime', 'unknown')
    global_risk = event_context.get('global_risk_level', 'unknown')
    event_regime = event_context.get('event_regime', 'unknown')
    defensive_bias = event_context.get('defensive_bias', 'neutral')
    quant = market_context.get('quant_indicators', {})
    strategy_alignment = f"{strategy.get('base_strategy', 'unknown')} / {strategy.get('scenario_overlay', 'unknown')}"
    tape_bias = tape_context.get('market_bias', 'unknown')

    # === Phase C: Load pre-generated decision reasoning (LLM or rule-engine) ===
    STATE_DIR = ROOT / 'instances' / 'etf_master' / 'state'
    pre_reasoning = {}
    dr_path = STATE_DIR / 'decision_reasoning.json'
    if dr_path.exists():
        try:
            pre_reasoning = json.loads(dr_path.read_text(encoding='utf-8'))
        except Exception:
            pre_reasoning = {}

    # === Build real market context reasoning ===
    rsi_dist = quant.get('rsi_distribution', {})
    macd_breadth = quant.get('macd_breadth', {})
    sma_struct = quant.get('sma_structure', {})
    group_trends = quant.get('group_trends', {})

    ctx_parts = []
    if market_regime != 'unknown':
        regime_desc = {
            'bullish': '偏多頭', 'balanced_bullish': '偏多但需謹慎',
            'balanced': '中性', 'cautious': '偏謹慎', 'defensive': '偏防守',
        }
        ctx_parts.append(f"市場 regime {regime_desc.get(market_regime, market_regime)}")
    if risk_temperature != 'unknown':
        ctx_parts.append(f"風險溫度 {risk_temperature}")
    if event_regime != 'unknown':
        ctx_parts.append(f"事件層 {event_regime}")
    if tape_bias != 'unknown':
        ctx_parts.append(f"盤感 {tape_bias}")
    if rsi_dist.get('avg'):
        ctx_parts.append(f"均RSI {rsi_dist['avg']}")
    if macd_breadth.get('direction'):
        ctx_parts.append(f"MACD {macd_breadth['direction']}")
    if sma_struct.get('structure'):
        ctx_parts.append(f"均線{sma_struct['structure']}")
    market_context_summary = '；'.join(ctx_parts) if ctx_parts else '市場數據不足，無法形成判斷。'
    if market_view_wiki:
        market_context_summary += '；已載入 Wiki 市場觀點背景'

    # Group trend insight
    group_insights = []
    for grp, trend in group_trends.items():
        avg_rsi = trend.get('avg_rsi')
        mom = trend.get('momentum')
        if avg_rsi or mom:
            group_insights.append(f"{grp}群（RSI {avg_rsi or '?'}，動能 {mom or '?'}）")
    group_summary = '；'.join(group_insights) if group_insights else '各群組趨勢資料待補。'

    # Active events from event context
    active_events = event_context.get('active_events', [])
    event_risk_parts = []
    if global_risk != 'unknown':
        event_risk_parts.append(f"全球風險 {global_risk}")
    if defensive_bias != 'neutral':
        event_risk_parts.append(f"防守傾向 {defensive_bias}")
    if active_events:
        event_risk_parts.append(f"關注：{'、'.join(active_events[:3])}")
    wm_sc = worldmonitor_context.get('supply_chain_stress', 'unknown')
    wm_geo = worldmonitor_context.get('geopolitical_risk', 'unknown')
    wm_tw = worldmonitor_context.get('taiwan_strait_risk', 'unknown')
    wm_alerts = int(worldmonitor_context.get('active_alerts_count', 0) or 0)
    wm_sev = worldmonitor_context.get('highest_alert_severity', 'none')
    if any(v != 'unknown' for v in [wm_sc, wm_geo, wm_tw]):
        event_risk_parts.append(f"worldmonitor:供應鏈={wm_sc}/地緣={wm_geo}/台海={wm_tw}")
    if wm_alerts > 0:
        event_risk_parts.append(f"worldmonitor 告警 {wm_alerts} 筆（最高 {wm_sev}）")
    if risk_signal_wiki:
        event_risk_parts.append("已載入 Wiki 風險訊號背景")
    risk_context_summary = '；'.join(event_risk_parts) if event_risk_parts else '外部事件風險數據不足。'

    if not intelligence:
        market_summary_final = pre_reasoning.get('market_context_summary') or market_context_summary
        risk_summary_final = pre_reasoning.get('risk_context_summary') or risk_context_summary
        if 'worldmonitor:' in risk_context_summary and 'worldmonitor:' not in risk_summary_final:
            risk_summary_final = f"{risk_summary_final}；{risk_context_summary}"
        reasoning = {
            'market_context_summary': market_summary_final,
            'position_context_summary': pre_reasoning.get('position_context_summary') or group_summary,
            'risk_context_summary': risk_summary_final,
            'reasoning_source': pre_reasoning.get('source', 'inline'),
            'learned_rules': '',
        }
        return {}, reasoning, '目前資料不足，先維持觀望。', 'hold', 'medium'

    # === Strategy-aware scoring tables (mirrors rule engine STRATEGY_WEIGHTS group preferences) ===
    STRATEGY_GROUP_BONUS: dict[str, dict[str, float]] = {
        '核心累積':  {'core': 1.5, 'growth': 1.0, 'income': 0.0, 'defensive': 0.0},
        '收益優先':  {'income': 2.0, 'core': 0.5, 'growth': 0.0, 'defensive': 0.5},
        '防守保守':  {'defensive': 2.0, 'income': 1.0, 'core': 0.0, 'growth': -1.0},
        '平衡配置':  {'core': 0.5, 'growth': 0.5, 'income': 0.5, 'defensive': 0.5},
        '觀察模式':  {},
    }

    # Scenario overlay modifiers (mirrors rule engine OVERLAY_MODIFIERS)
    OVERLAY_AI_MODS: dict[str, dict] = {
        '減碼保守':  {'score_penalty': 1.0},
        '高波動警戒': {'score_cap': 4.0},
        '逢低觀察':  {'rsi_bonus_threshold': 40, 'rsi_bonus': 1.0},
    }

    base_strategy_name = strategy.get('base_strategy', '')
    scenario_overlay_name = strategy.get('scenario_overlay', '') or ''
    group_bonus_map = STRATEGY_GROUP_BONUS.get(base_strategy_name, {})
    overlay_mods = OVERLAY_AI_MODS.get(scenario_overlay_name, {})

    # === Candidate selection: multi-dimensional (not just RSI) ===
    # Score each symbol using TOMO 三原則 + technical signals
    scored = []
    for sym, m in intelligence.items():
        s = 0.0
        # Value: low RSI = undervalued (moderate, not extreme)
        rsi = m.get('rsi', 50)
        if isinstance(rsi, (int, float)):
            if 30 <= rsi <= 45:
                s += 2  # Sweet spot: undervalued but not panic
            elif 45 < rsi <= 55:
                s += 1
            elif rsi > 75:
                s -= 1  # Overbought

        # Momentum: positive momentum preferred
        mom = m.get('momentum_20d', 0)
        if isinstance(mom, (int, float)):
            if mom > 5:
                s += 2
            elif mom > 1:
                s += 1
            elif mom < -5:
                s -= 1

        # Track record: Sharpe & 1y return
        sharpe = m.get('sharpe_30d', 0)
        ret_1y = m.get('return_1y', 0)
        if isinstance(sharpe, (int, float)) and sharpe > 0.5:
            s += 1
        elif isinstance(sharpe, (int, float)) and sharpe < -0.5:
            s -= 1
        if isinstance(ret_1y, (int, float)) and ret_1y > 15:
            s += 1
        elif isinstance(ret_1y, (int, float)) and ret_1y < -10:
            s -= 1

        # BB position: near lower band = potential value
        price = m.get('last_price', 0)
        bb_lower = m.get('bb_lower', 0)
        bb_upper = m.get('bb_upper', 0)
        if all(isinstance(x, (int, float)) and x > 0 for x in [price, bb_lower, bb_upper]):
            bb_pct = (price - bb_lower) / max(bb_upper - bb_lower, 0.01)
            if bb_pct < 0.2:
                s += 1  # Near lower band

        # Strategy group bonus: align scoring with current base_strategy
        sym_group = m.get('group', '')
        if sym_group and group_bonus_map:
            s += group_bonus_map.get(sym_group, 0.0)

        # Overlay modifiers
        if overlay_mods.get('rsi_bonus_threshold') and isinstance(rsi, (int, float)):
            if rsi <= overlay_mods['rsi_bonus_threshold']:
                s += overlay_mods.get('rsi_bonus', 0.0)
        if 'score_penalty' in overlay_mods:
            s -= overlay_mods['score_penalty']

        scored.append((sym, s, m))

    # Apply score_cap overlay (cap each symbol's score)
    if 'score_cap' in overlay_mods:
        cap = overlay_mods['score_cap']
        scored = [(sym, min(s, cap), m) for sym, s, m in scored]

    scored.sort(key=lambda x: x[1], reverse=True)

    # === Phase D: Load wiki background for top candidates ===
    wiki_context: dict[str, str] = {}
    for sym, _, _ in scored[:3]:
        wiki_text = _resolve_entity_wiki_text(sym, request_payload, limit=800)
        if wiki_text:
            wiki_context[sym] = wiki_text

    if not scored:
        reasoning = {
            'market_context_summary': market_context_summary,
            'position_context_summary': group_summary,
            'risk_context_summary': risk_context_summary,
            'learned_rules': '',
        }
        return {}, reasoning, '無可用候選，維持觀望。', 'hold', 'medium'

    symbol, ai_score, metrics = scored[0]
    wiki_note = ''
    if wiki_context.get(symbol):
        first_section = next(
            (ln.strip() for ln in wiki_context[symbol].splitlines() if ln.startswith('## ')),
            ''
        )
        wiki_note = f'；Wiki分類: {first_section[3:]}' if first_section else ''
    # Build dimension detail for reasoning
    dim_parts = []
    rsi_v = metrics.get('rsi', 50)
    mom_v = metrics.get('momentum_20d')
    sharpe_v = metrics.get('sharpe_30d')
    ret_v = metrics.get('return_1y')
    if isinstance(rsi_v, (int, float)):
        dim_parts.append(f"RSI {rsi_v:.0f}")
    if isinstance(mom_v, (int, float)):
        dim_parts.append(f"動能 {mom_v:+.1f}%")
    if isinstance(sharpe_v, (int, float)):
        dim_parts.append(f"夏普 {sharpe_v:.1f}")
    if isinstance(ret_v, (int, float)):
        dim_parts.append(f"1年報酬 {ret_v:+.0f}%")
    dim_summary = '、'.join(dim_parts) if dim_parts else '指標資料待補'

    # Determine if top candidate aligns with current strategy group preference
    top_group = metrics.get('group', '')
    if group_bonus_map and top_group:
        _bonus = group_bonus_map.get(top_group, 0.0)
        strategy_aligned_flag = _bonus > 0.0
    elif not group_bonus_map:
        # 觀察模式 or unknown strategy — neutral alignment
        strategy_aligned_flag = None
    else:
        strategy_aligned_flag = False

    candidate = {
        'symbol': symbol,
        'side': 'buy',
        'reference_price': metrics.get('last_price'),
        'quantity': 100,
        'reason': f'AI agent 判斷：{symbol} 多維度評分 {ai_score:.1f}（{dim_summary}），符合 TOMO 三原則，可列入 preview。{wiki_note}',
        'risk_note': f'risk_temperature={risk_temperature}；event_regime={event_regime}；仍屬建議層。',
        'strategy_aligned': strategy_aligned_flag,
        'strategy_group': top_group or None,
    }

    memory_notes = decision_memory_context.get('memory_notes') or []
    quality_hooks = decision_memory_context.get('quality_hooks') or {}
    quality_state = quality_state or {}
    superseded_hits = sum(1 for n in memory_notes if n.get('review_status') == 'superseded')
    reviewed_hits = sum(1 for n in memory_notes if n.get('review_status') == 'reviewed')

    # Confidence from multi-dimensional signals (not just RSI)
    if ai_score >= 4:
        confidence = 'high'
    elif ai_score >= 2:
        confidence = 'medium'
    else:
        confidence = 'low'

    summary = f'AI agent 建議優先觀察 {symbol}（{dim_summary}），可建立 preview 候選。'
    # Confidence bias from quality state or hooks
    confidence_bias = quality_state.get('confidence_bias') or quality_hooks.get('confidence_bias')
    if confidence_bias == 'lower' or superseded_hits >= 2:
        if confidence == 'high':
            confidence = 'medium'
        elif confidence == 'medium':
            confidence = 'low'
        # If low, remains low
        
        if superseded_hits >= 2:
            summary += ' 最近反思顯示此類建議穩定度不足，需降低信心。'
        else:
            summary += ' quality hooks 顯示近期 preview_buy 穩定度偏弱。'
    elif confidence_bias == 'raise_if_supported' and ai_score >= 4:
        confidence = 'high'
    elif reviewed_hits >= 1 and confidence != 'low':
        summary += ' 最近反思顯示此方向可延續觀察。'

    market_summary_final = pre_reasoning.get('market_context_summary') or market_context_summary
    risk_summary_final = pre_reasoning.get('risk_context_summary') or risk_context_summary
    if 'worldmonitor:' in risk_context_summary and 'worldmonitor:' not in risk_summary_final:
        risk_summary_final = f"{risk_summary_final}；{risk_context_summary}"

    reasoning = {
        'market_context_summary': market_summary_final,
        'position_context_summary': pre_reasoning.get('position_context_summary') or group_summary,
        'risk_context_summary': risk_summary_final,
        'reasoning_source': pre_reasoning.get('source', 'inline'),
        'learned_rules': learned_rules_draft,
    }
    return candidate, reasoning, summary, 'preview_buy', confidence, strategy_alignment


def generate_ai_agent_response_from_state_dir(state_dir: Path, agent_name: str = 'ETF_Master') -> dict:
    request_payload = _load_json(state_dir / 'ai_decision_request.json')
    quality_state = _load_json(state_dir / 'ai_decision_quality.json')
    result = _build_agent_reasoning(request_payload, quality_state=quality_state)
    if len(result) == 5:
        candidate, reasoning, summary, action, confidence = result
        strategy_alignment = 'unknown / unknown'
    else:
        candidate, reasoning, summary, action, confidence, strategy_alignment = result
    input_fingerprint = request_payload.get('input_fingerprint', '')
    payload = build_agent_consumed_response_payload(
        request_id=request_payload.get('request_id', 'missing-request-id'),
        summary=summary,
        action=action,
        confidence=confidence,
        agent_name=agent_name,
        review_status='pending',
        reasoning=reasoning,
        input_refs={'request': 'ai_decision_request.json', 'input_fingerprint': input_fingerprint},
        candidate=candidate,
        strategy_alignment=strategy_alignment,
        warnings=[],
    )
    (state_dir / 'ai_decision_response.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


if __name__ == '__main__':
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / 'instances' / 'etf_master' / 'state')
    agent_name = sys.argv[2] if len(sys.argv) > 2 else 'ETF_Master'
    payload = generate_ai_agent_response_from_state_dir(target_dir, agent_name=agent_name)
    print(json.dumps({"ok": True, "request_id": payload.get('request_id'), "source": payload.get('source')}, ensure_ascii=False))
