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


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _pick_candidate(request_payload: dict) -> tuple[dict, str, str, str]:
    inputs = request_payload.get('inputs', {})
    intelligence = (inputs.get('market_intelligence') or {}).get('intelligence') or {}
    strategy = inputs.get('strategy') or {}
    risk_temperature = (inputs.get('market_context_taiwan') or {}).get('risk_temperature', 'unknown')
    global_risk = (inputs.get('market_event_context') or {}).get('global_risk_level', 'unknown')

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
    base_strategy = strategy.get('base_strategy', 'unknown')
    overlay = strategy.get('scenario_overlay', 'unknown')
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
