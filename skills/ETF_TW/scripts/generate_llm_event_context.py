#!/usr/bin/env python3
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

"""
generate_llm_event_context.py — LLM 增強版市場事件情境

當 LLM API 可用時：用新聞頭條+技術指標+宏觀數據 產出結構化判斷
當 LLM 不可用時：fallback 到規則引擎 (generate_market_event_context.py)

LLM 輸出格式：
{
  "event_regime": "risk-on|neutral|cautious|risk-off",
  "global_risk_level": "normal|moderate|elevated",
  "geo_political_risk": "low|medium|high",
  "rate_risk": "low|medium|high",
  "energy_risk": "low|medium|high",
  "defensive_bias": "low|medium|high",
  "active_events": ["...", ...],
  "llm_reasoning": "人類可讀的政經判斷",
  "confidence": "low|medium|high"
}

寫入 state/market_event_context.json（覆蓋規則引擎版本）
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from etf_core.state_io import safe_load_json, atomic_save_json
from etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
OUTPUT_PATH = STATE / 'market_event_context.json'


def _build_llm_prompt(news: dict, macro: dict, calendar: dict, intel_breadth: dict, current_event_ctx: dict) -> str:
    """Build a structured prompt for LLM to generate market event context."""
    parts = []
    parts.append("你是一位專業的台股 ETF 市場事件分析師。根據以下資料，產出結構化的市場事件情境判斷。")
    parts.append("")
    parts.append("## 輸出格式（嚴格 JSON）")
    parts.append("""{
  "event_regime": "risk-on|neutral|cautious|risk-off",
  "global_risk_level": "normal|moderate|elevated",
  "geo_political_risk": "low|medium|high",
  "rate_risk": "low|medium|high",
  "energy_risk": "low|medium|high",
  "defensive_bias": "low|medium|high",
  "active_events": ["事件1", "事件2"],
  "llm_reasoning": "一段50-100字的人類可讀政經判斷",
  "confidence": "low|medium|high"
}""")
    parts.append("")
    parts.append("## 新聞頭條")
    headlines = news.get('headlines', [])
    if headlines:
        for h in headlines[:10]:
            tags_str = ','.join(h.get('tags', [])) if h.get('tags') else ''
            parts.append(f"- [{h.get('sentiment','?')}] {h.get('title','')} [{tags_str}]")
    else:
        parts.append("(無新聞資料)")
    parts.append("")

    parts.append("## 宏觀指標")
    parts.append(f"- TAIEX 趨勢: {macro.get('taiex_trend', 'unknown')}")
    vix = macro.get('vix_proxy')
    parts.append(f"- VIX proxy: {vix if vix else 'N/A'}")
    breadth = macro.get('market_breadth', {})
    parts.append(f"- 市場寬度: {breadth.get('breadth', 'unknown')}")
    parts.append("")

    parts.append("## 央行日曆")
    next_major = calendar.get('next_major')
    if next_major:
        parts.append(f"- 最近重大會議: {next_major.get('event', '')} ({next_major.get('days_until', '?')}天後)")
    else:
        parts.append("(無近期會議)")
    parts.append("")

    parts.append("## 技術面寬度（規則引擎推算）")
    parts.append(f"- 多頭%: {intel_breadth.get('bullish_pct', 0)}%")
    parts.append(f"- 空頭%: {intel_breadth.get('bearish_pct', 0)}%")
    parts.append(f"- 均RSI: {intel_breadth.get('avg_rsi', 0)}")
    parts.append("")

    parts.append("## 規則引擎基準判斷（供參考，可覆蓋）")
    parts.append(f"- event_regime: {current_event_ctx.get('event_regime', '?')}")
    parts.append(f"- global_risk_level: {current_event_ctx.get('global_risk_level', '?')}")
    parts.append(f"- geo_political_risk: {current_event_ctx.get('geo_political_risk', '?')}")
    parts.append(f"- rate_risk: {current_event_ctx.get('rate_risk', '?')}")
    parts.append("")
    parts.append("請直接輸出 JSON，不要加 markdown code block。")

    return '\n'.join(parts)


def _call_llm(prompt: str) -> str | None:
    """Try to call an LLM API. Returns response text or None.
    
    Strategy order:
    1. Ollama HTTP API (localhost:11434) — fastest, local
    2. OpenAI-compatible API (env vars) — cloud
    3. Ollama CLI (fallback) — may hang in sandbox
    """
    import shutil
    model = os.environ.get('LLM_MODEL') or os.environ.get('OPENAI_MODEL') or 'glm-5:cloud'

    # Strategy 1: Ollama HTTP API (localhost)
    try:
        import requests as req
        # Quick check daemon is alive
        alive = req.get('http://localhost:11434/api/tags', timeout=3)
        if alive.status_code == 200:
            models = [m.get('name', '') for m in alive.json().get('models', [])]
            # Prefer glm-5:cloud if available, else first available
            if model not in models:
                # Try partial match
                candidates = [m for m in models if 'glm' in m] or models
                if candidates:
                    model = candidates[0]
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '你是台股 ETF 市場事件分析師，輸出嚴格 JSON。'},
                    {'role': 'user', 'content': prompt},
                ],
                'stream': False,
                'options': {'temperature': 0.3},
            }
            resp = req.post('http://localhost:11434/api/chat', json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get('message', {}).get('content', '')
                if content.strip():
                    print(f"  [LLM] ollama HTTP OK (model={model})")
                    return content.strip()
            else:
                print(f"  [LLM] ollama HTTP {resp.status_code}: {resp.text[:200]}")
        else:
            print(f"  [LLM] ollama daemon check failed: {alive.status_code}")
    except Exception as e:
        print(f"  [LLM] ollama HTTP failed: {e}")

    # Strategy 2: OpenAI-compatible API (cloud)
    api_base = os.environ.get('LLM_API_BASE') or os.environ.get('OPENAI_API_BASE')
    api_key = os.environ.get('LLM_API_KEY') or os.environ.get('OPENAI_API_KEY') or 'dummy'

    if api_base:
        try:
            import requests as req
            url = f"{api_base.rstrip('/')}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            }
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '你是台股 ETF 市場事件分析師，輸出嚴格 JSON。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.3,
                'max_tokens': 500,
            }
            resp = req.post(url, json=payload, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"  [LLM] cloud API {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  [LLM] cloud API failed: {e}")

    # Strategy 3: Ollama CLI (slower, may hang in sandbox)
    if shutil.which('ollama') is not None:
        import subprocess
        try:
            check = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=3)
            if check.returncode == 0:
                result = subprocess.run(
                    ['ollama', 'run', model, prompt],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
        except Exception:
            print("  [LLM] ollama CLI failed, skipping")

    return None


def _parse_llm_response(text: str) -> dict | None:
    """Parse LLM JSON response. Tolerant of markdown fences."""
    # Strip markdown code blocks if present
    cleaned = text.strip()
    if cleaned.startswith('```'):
        # Remove first and last line
        lines = cleaned.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        cleaned = '\n'.join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = cleaned.find('{')
        end = cleaned.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass

    print(f"  [LLM] Failed to parse response: {cleaned[:200]}")
    return None


def _validate_llm_output(parsed: dict) -> dict | None:
    """Validate and normalize LLM output fields."""
    valid_regimes = {'risk-on', 'neutral', 'cautious', 'risk-off'}
    valid_risks = {'low', 'medium', 'high'}
    valid_levels = {'normal', 'moderate', 'elevated'}
    valid_biases = {'low', 'medium', 'high'}
    valid_conf = {'low', 'medium', 'high'}

    result = {}
    result['event_regime'] = parsed.get('event_regime', 'neutral') if parsed.get('event_regime') in valid_regimes else 'neutral'
    result['global_risk_level'] = parsed.get('global_risk_level', 'normal') if parsed.get('global_risk_level') in valid_levels else 'normal'
    result['geo_political_risk'] = parsed.get('geo_political_risk', 'low') if parsed.get('geo_political_risk') in valid_risks else 'low'
    result['rate_risk'] = parsed.get('rate_risk', 'low') if parsed.get('rate_risk') in valid_risks else 'low'
    result['energy_risk'] = parsed.get('energy_risk', 'low') if parsed.get('energy_risk') in valid_risks else 'low'
    result['defensive_bias'] = parsed.get('defensive_bias', 'low') if parsed.get('defensive_bias') in valid_biases else 'low'
    result['active_events'] = parsed.get('active_events', []) if isinstance(parsed.get('active_events'), list) else []
    result['llm_reasoning'] = str(parsed.get('llm_reasoning', ''))[:200]
    result['confidence'] = parsed.get('confidence', 'medium') if parsed.get('confidence') in valid_conf else 'medium'

    return result


def generate_llm_event_context() -> dict:
    """Main entry: try LLM, fallback to rule engine."""
    now = datetime.now(TW_TZ)

    # Load all data sources
    news = safe_load_json(STATE / 'news_headlines.json', {})
    macro = safe_load_json(STATE / 'macro_indicators.json', {})
    calendar = safe_load_json(STATE / 'central_bank_calendar.json', {})
    current_event = safe_load_json(STATE / 'market_event_context.json', {})
    intel_data = safe_load_json(STATE / 'market_intelligence.json', {'intelligence': {}})

    # Extract breadth from current event context
    breadth = current_event.get('breadth', {})

    # Try LLM
    prompt = _build_llm_prompt(news, macro, calendar, breadth, current_event)
    llm_text = _call_llm(prompt)

    if llm_text:
        parsed = _parse_llm_response(llm_text)
        if parsed:
            validated = _validate_llm_output(parsed)
            # Merge with rule-engine results: LLM can override regime/risks
            payload = {
                **current_event,  # Preserve existing fields (breadth, summary, etc.)
                'event_regime': validated['event_regime'],
                'global_risk_level': validated['global_risk_level'],
                'geo_political_risk': validated['geo_political_risk'],
                'rate_risk': validated['rate_risk'],
                'energy_risk': validated['energy_risk'],
                'defensive_bias': validated['defensive_bias'],
                'active_events': validated['active_events'] or current_event.get('active_events', []),
                'llm_reasoning': validated['llm_reasoning'],
                'llm_confidence': validated['confidence'],
                'source': 'llm-enhanced-v1',
                'updated_at': now.isoformat(),
            }
            atomic_save_json(OUTPUT_PATH, payload)
            print(f"LLM_EVENT_CONTEXT_OK: regime={validated['event_regime']}, risk={validated['global_risk_level']}, confidence={validated['confidence']}")
            print(f"  LLM reasoning: {validated['llm_reasoning'][:100]}")
            return payload

    # Fallback: rule engine already ran, just mark as such
    print("LLM_EVENT_CONTEXT_FALLBACK: LLM unavailable, using rule engine results")
    fallback = {
        **current_event,
        'llm_reasoning': '(LLM 不可用，由規則引擎推算)',
        'llm_confidence': 'low',
        'source': 'rule-engine-fallback-v1',
        'updated_at': now.isoformat(),
    }
    atomic_save_json(OUTPUT_PATH, fallback)
    return fallback


if __name__ == '__main__':
    generate_llm_event_context()