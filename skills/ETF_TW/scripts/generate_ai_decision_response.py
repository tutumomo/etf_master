#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from scripts.ai_decision_bridge import build_ai_decision_response
from scripts.provenance_logger import build_provenance_record, append_provenance

PROVENANCE_PATH = None  # set later from state_dir

STRATEGY_GROUP_WEIGHTS = {
    '核心累積': {'core': 3.0, 'income': 1.5, 'defensive': 1.5, 'growth': 2.0, 'smart_beta': 1.5, 'other': 1.0},
    '收益優先': {'core': 1.5, 'income': 3.0, 'defensive': 2.0, 'growth': 1.0, 'smart_beta': 1.5, 'other': 1.0},
    '平衡配置': {'core': 2.0, 'income': 2.0, 'defensive': 2.0, 'growth': 1.5, 'smart_beta': 1.5, 'other': 1.0},
    '防守保守': {'core': 1.5, 'income': 1.5, 'defensive': 3.0, 'growth': 0.5, 'smart_beta': 1.0, 'other': 0.5},
    '觀察模式': {'core': 1.0, 'income': 1.0, 'defensive': 1.0, 'growth': 1.0, 'smart_beta': 1.0, 'other': 1.0},
}

OVERLAY_GROUP_MODIFIERS = {
    '收益再投資': {'income': 1.0, 'core': 0.5, 'growth': -0.5},
    '逢低觀察': {'core': 0.5, 'income': 0.5, 'defensive': 0.5, 'growth': 0.5, 'smart_beta': 0.5},
    '高波動警戒': {'defensive': 2.0, 'core': 0.5, 'income': 0.5, 'growth': -2.0, 'smart_beta': -1.0},
    '高波動防守': {'defensive': 2.0, 'core': 0.5, 'income': 0.5, 'growth': -2.0, 'smart_beta': -1.0},
    '減碼保守': {'defensive': 1.5, 'income': 0.5, 'growth': -1.5, 'smart_beta': -1.0},
    '無': {},
}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _candidate_group(item: dict) -> str:
    group = item.get('watchlist_group')
    if group:
        return group
    if item.get('asset_class') == 'bond':
        return 'defensive'
    tags = set(item.get('strategy_tags') or [])
    if 'income' in tags:
        return 'income'
    if 'tech' in tags:
        return 'growth'
    if item.get('asset_class') == 'equity':
        return 'core'
    return 'other'


def _metric_score(metrics: dict) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []

    rsi = metrics.get('rsi')
    if isinstance(rsi, (int, float)):
        if rsi <= 45:
            score += 2.0
            reasons.append(f'RSI {rsi:.0f} 偏低，具逢低觀察價值')
        elif rsi <= 55:
            score += 1.0
            reasons.append(f'RSI {rsi:.0f} 中性偏低')
        elif rsi >= 70:
            score -= 2.0
            reasons.append(f'RSI {rsi:.0f} 偏高，避免追價')

    momentum = metrics.get('momentum_20d')
    if isinstance(momentum, (int, float)):
        if momentum > 5:
            score += 1.0
            reasons.append(f'20日動能 +{momentum:.1f}%')
        elif momentum < -5:
            score -= 1.0
            reasons.append(f'20日動能 {momentum:.1f}%，短線偏弱')

    sharpe = metrics.get('sharpe_30d')
    if isinstance(sharpe, (int, float)):
        if sharpe > 2:
            score += 1.0
            reasons.append(f'夏普值 {sharpe:.1f} 佳')
        elif sharpe < -0.5:
            score -= 1.0
            reasons.append(f'夏普值 {sharpe:.1f} 偏弱')

    return score, reasons


def _score_watchlist_candidate(item: dict, strategy: dict, risk_temperature: str, global_risk: str) -> dict:
    base_strategy = strategy.get('base_strategy') or '平衡配置'
    overlay = strategy.get('scenario_overlay') or '無'
    group = _candidate_group(item)
    weights = STRATEGY_GROUP_WEIGHTS.get(base_strategy, STRATEGY_GROUP_WEIGHTS['平衡配置'])
    score = float(weights.get(group, weights.get('other', 1.0)))
    reasons = [f'符合 {base_strategy} 的 {group} 權重 {score:.1f}']

    overlay_delta = OVERLAY_GROUP_MODIFIERS.get(overlay, {}).get(group, 0)
    if overlay_delta:
        score += overlay_delta
        reasons.append(f'情境「{overlay}」調整 {overlay_delta:+.1f}')

    if risk_temperature in {'elevated', 'high'} or global_risk in {'elevated', 'high'}:
        if group == 'defensive':
            score += 1.0
            reasons.append('風險升高，防守型加分')
        else:
            score -= 1.0
            reasons.append('風險升高，非防守型降分')

    metric_delta, metric_reasons = _metric_score(item.get('market_metrics') or {})
    score += metric_delta
    reasons.extend(metric_reasons)

    if item.get('is_held'):
        score -= 1.0
        reasons.append('已有持倉，降低新增優先度')

    return {
        'symbol': item.get('symbol'),
        'name': item.get('name'),
        'group': group,
        'score': round(score, 2),
        'reasons': reasons,
        'item': item,
    }


def _eligible_groups(strategy: dict) -> set[str]:
    base_strategy = strategy.get('base_strategy') or '平衡配置'
    overlay = strategy.get('scenario_overlay') or '無'
    if base_strategy == '核心累積':
        return {'core', 'growth'}
    if base_strategy == '收益優先':
        if overlay in {'高波動警戒', '高波動防守', '減碼保守'}:
            return {'income', 'defensive'}
        return {'income', 'smart_beta'}
    if base_strategy == '防守保守':
        return {'defensive'}
    if base_strategy == '平衡配置':
        return {'core', 'income', 'defensive', 'smart_beta'}
    return {'core', 'income', 'defensive', 'growth', 'smart_beta', 'other'}


def _pick_candidate(request_payload: dict) -> tuple[dict, str, str, str]:
    inputs = request_payload.get('inputs', {})
    intelligence = (inputs.get('market_intelligence') or {}).get('intelligence') or {}
    strategy = inputs.get('strategy') or {}
    risk_temperature = (inputs.get('market_context_taiwan') or {}).get('risk_temperature', 'unknown')
    global_risk = (inputs.get('market_event_context') or {}).get('global_risk_level', 'unknown')
    watchlist_items = (inputs.get('watchlist_context') or {}).get('items') or []
    base_strategy = strategy.get('base_strategy', 'unknown')
    overlay = strategy.get('scenario_overlay', 'unknown')

    if base_strategy == '觀察模式':
        return {}, '觀察模式啟用中，AI Bridge 僅更新脈絡，不建立 preview 候選。', 'watch_only', 'medium'

    if watchlist_items:
        eligible = _eligible_groups(strategy)
        scored_all = [
            _score_watchlist_candidate(item, strategy, risk_temperature, global_risk)
            for item in watchlist_items
        ]
        scored = sorted(
            (row for row in scored_all if row['group'] in eligible),
            key=lambda row: row['score'],
            reverse=True,
        )
        if not scored:
            return {}, f"AI Bridge 依 {base_strategy} / {overlay} 過濾後，沒有符合策略群組的候選。", 'hold', 'medium'
        best = scored[0]
        threshold = 5.0 if risk_temperature in {'elevated', 'high'} else 4.0
        item = best['item']
        metrics = item.get('market_metrics') or {}
        candidate = {
            'symbol': best['symbol'],
            'side': 'buy' if best['score'] > threshold else 'watch',
            'reference_price': metrics.get('current_price') or metrics.get('last_price'),
            'quantity': 100,
            'reason': '；'.join(best['reasons']),
            'risk_note': f"AI Bridge 依 watchlist_context、{base_strategy}/{overlay} 與市場風險評分；仍屬建議層，未自動送單。",
            'score': best['score'],
            'group': best['group'],
        }
        if best['score'] <= threshold:
            summary = f"AI Bridge 建議觀察 {best['symbol']}，策略分數 {best['score']:.1f} 未高於買進門檻 {threshold:.1f}。"
            return candidate, summary, 'watch_only', 'medium'

        confidence = 'high' if best['score'] >= threshold + 2 else 'medium'
        summary = f"AI Bridge 建議優先觀察 {best['symbol']}，策略分數 {best['score']:.1f}，可建立 preview 候選。"
        return candidate, summary, 'preview_buy', confidence

    if not intelligence:
        return {}, '目前資料不足，先維持觀望。', 'hold', 'medium'

    ranked = sorted(intelligence.items(), key=lambda kv: kv[1].get('rsi', 50))
    symbol, metrics = ranked[0]
    candidate = {
        'symbol': symbol,
        'side': 'buy',
        'reference_price': metrics.get('close'),
        'quantity': 100,
        'reason': f"依目前 AI Decision Bridge 最小規則，{symbol} 在可用 intelligence 中相對偏低檔，可列入 preview 觀察。",
        'risk_note': f"目前 risk_temperature={risk_temperature}；global_risk_level={global_risk}；仍屬建議層，未自動送單。",
    }
    summary = f"建議優先觀察 {symbol}，可建立 preview 候選。"
    confidence = 'high' if metrics.get('rsi', 50) < 45 else 'medium'
    return candidate, summary, 'preview_buy', confidence


def generate_response_payload_from_state_dir(state_dir: Path) -> dict:
    request_payload = _load_json(state_dir / 'ai_decision_request.json')
    candidate, summary, action, confidence = _pick_candidate(request_payload)
    strategy = (request_payload.get('inputs') or {}).get('strategy') or {}
    payload = build_ai_decision_response(
        request_id=request_payload.get('request_id', 'missing-request-id'),
        summary=summary,
        action=action,
        confidence=confidence,
        strategy_alignment=f"{strategy.get('base_strategy', 'unknown')} / {strategy.get('scenario_overlay', 'unknown')}",
        candidate=candidate,
        warnings=[],
        input_refs={'request': 'ai_decision_request.json'},
    )
    (state_dir / 'ai_decision_response.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    # --- Provenance: record every decision cycle ---
    provenance_path = state_dir / 'decision_provenance.jsonl'
    try:
        record = build_provenance_record(
            request_payload=request_payload,
            response_payload=payload,
            scan_result=None,
            source='generate_ai_decision_response',
        )
        append_provenance(provenance_path, record)
    except Exception as e:
        import warnings
        warnings.warn(f"[provenance] Failed to append provenance record: {e}")

    return payload


if __name__ == '__main__':
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / 'instances' / 'etf_master' / 'state')
    payload = generate_response_payload_from_state_dir(target_dir)
    print(json.dumps({"ok": True, "request_id": payload.get('request_id'), "action": payload.get('decision', {}).get('action')}, ensure_ascii=False))
