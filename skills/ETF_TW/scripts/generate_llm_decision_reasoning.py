#!/usr/bin/env python3
from __future__ import annotations
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

"""
generate_llm_decision_reasoning.py — LLM 增強版決策推理

將市場事件情境 + 宏觀指標 + 新聞 → 注入 decide_action 的推理鏈
使 AI agent 的 reasoning 不再是空殼，而是真實政經判斷

當 LLM 不可用 → 用規則引擎自動摘要 fallback

寫入 state/decision_reasoning.json
供 generate_ai_agent_response.py 的 _build_agent_reasoning() 讀取
"""

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
OUTPUT_PATH = STATE / 'decision_reasoning.json'


def _build_rule_based_reasoning(event_ctx: dict, macro: dict, calendar: dict, news: dict, intel: dict) -> dict:
    """Rule-engine fallback: auto-generate reasoning from data (no LLM needed)."""
    parts_market = []
    parts_risk = []
    parts_position = []

    # Market regime
    regime = event_ctx.get('event_regime', 'unknown')
    regime_desc = {
        'risk-on': '市場處於偏多格局，技術信號健康',
        'neutral': '市場氣氛中性，方向不明',
        'cautious': '市場氣氛偏謹慎，宜降低風險',
        'risk-off': '市場偏空頭，風險偏好明顯下降',
    }
    parts_market.append(regime_desc.get(regime, '市場狀態不明'))

    # Macro context
    trend = macro.get('taiex_trend', 'unknown')
    vix = macro.get('vix_proxy')
    breadth_data = macro.get('market_breadth', {})
    m_breadth = breadth_data.get('breadth', 'unknown')

    if trend == 'up':
        parts_market.append('加權指數趨勢偏多（ETF動能代理）')
    elif trend == 'down':
        parts_market.append('加權指數趨勢偏空（ETF動能代理）')
    if isinstance(vix, (int, float)):
        if vix > 20:
            parts_market.append(f'波動率代理偏高（{vix}），市場不安')
        elif vix < 12:
            parts_market.append(f'波動率代理偏低（{vix}），市場偏平靜')

    # Event context details
    event_regime = event_ctx.get('event_regime', 'unknown')
    global_risk = event_ctx.get('global_risk_level', 'unknown')
    geo_risk = event_ctx.get('geo_political_risk', 'unknown')
    rate_risk = event_ctx.get('rate_risk', 'unknown')
    defensive_bias = event_ctx.get('defensive_bias', 'neutral')

    parts_risk.append(f'全風險={global_risk}，地緣={geo_risk}，利率={rate_risk}')
    if defensive_bias in ('medium', 'high'):
        parts_risk.append(f'防守傾向={defensive_bias}，建議提高保守權重')

    # Calendar
    next_major = calendar.get('next_major')
    if next_major:
        days = next_major.get('days_until', 99)
        if days <= 14:
            parts_risk.append(f'{next_major["event"]}（{days}天後），利率決策風險升溫')

    # News sentiment
    tag_counts = news.get('tag_counts', {})
    sentiment = news.get('sentiment_counts', {})
    bear = sentiment.get('bearish', 0)
    bull = sentiment.get('bullish', 0)
    if bear + bull > 0:
        if bear > bull + 2:
            parts_risk.append(f'新聞情緒偏空（空{bear} vs 多{bull}），留意利空訊息')
        elif bull > bear + 2:
            parts_market.append(f'新聞情緒偏多（多{bull} vs 空{bear}），市場氛圍正向')

    if tag_counts.get('rate_decision', 0) >= 1:
        parts_risk.append(f'利率決策相關新聞 {tag_counts["rate_decision"]} 則')
    if tag_counts.get('geo_risk', 0) >= 1:
        parts_risk.append(f'地緣風險相關新聞 {tag_counts["geo_risk"]} 則')

    # Position context: ETF intelligence summary
    group_stats = {}
    for sym, m in intel.items():
        # Simple group mapping
        group = 'other'
        if sym in ('0050', '006208', '00713'):
            group = 'core'
        elif sym in ('00892', '00733B', '00679B'):
            group = 'income'
        elif sym in ('00679B',):
            group = 'defensive'
        elif sym in ('00923', '00891'):
            group = 'growth'

        if group not in group_stats:
            group_stats[group] = {'count': 0, 'avg_rsi': 0, 'avg_mom': 0}
        g = group_stats[group]
        g['count'] += 1
        rsi = m.get('rsi', 50)
        mom = m.get('momentum_20d', 0)
        if isinstance(rsi, (int, float)):
            g['avg_rsi'] = (g['avg_rsi'] * (g['count'] - 1) + rsi) / g['count']
        if isinstance(mom, (int, float)):
            g['avg_mom'] = (g['avg_mom'] * (g['count'] - 1) + mom) / g['count']

    for grp, stats in group_stats.items():
        if stats['count'] > 0:
            parts_position.append(f"{grp}群（{stats['count']}檔，RSI {stats['avg_rsi']:.0f}，動能 {stats['avg_mom']:+.1f}%）")

    return {
        'market_context_summary': '。'.join(parts_market) if parts_market else '市場數據不足。',
        'risk_context_summary': '。'.join(parts_risk) if parts_risk else '風險數據不足。',
        'position_context_summary': '；'.join(parts_position) if parts_position else '持倉推理待補。',
        'source': 'rule-engine-v1',
    }


def _build_llm_prompt(reasoning_data: dict, event_ctx: dict) -> str:
    """Build prompt for LLM to generate political-economic reasoning."""
    parts = []
    parts.append("你是一位資深台股 ETF 分析師。根據以下市場數據，寫出三段簡短的政經判斷。")
    parts.append("")
    parts.append("請輸出嚴格 JSON：")
    parts.append("""{
  "market_context_summary": "50字以內的市場情境判斷",
  "risk_context_summary": "50字以內的風險評估",
  "position_context_summary": "50字以內的持倉策略建議"
}""")
    parts.append("")
    parts.append("## 目前數據")
    parts.append(f"市場情境：{event_ctx.get('event_regime', '?')}")
    parts.append(f"風險等級：{event_ctx.get('global_risk_level', '?')}")
    parts.append(f"地緣風險：{event_ctx.get('geo_political_risk', '?')}")
    parts.append(f"利率風險：{event_ctx.get('rate_risk', '?')}")
    parts.append(f"防守傾向：{event_ctx.get('defensive_bias', '?')}")
    parts.append(f"規則引擎市場判斷：{reasoning_data.get('market_context_summary', '?')}")
    parts.append(f"規則引擎風險判斷：{reasoning_data.get('risk_context_summary', '?')}")
    parts.append(f"規則引擎持倉判斷：{reasoning_data.get('position_context_summary', '?')}")

    if event_ctx.get('llm_reasoning'):
        parts.append(f"前次 LLM 判斷：{event_ctx['llm_reasoning']}")

    parts.append("")
    parts.append("請直接輸出 JSON，不要加 markdown。")
    return '\n'.join(parts)


def _call_llm(prompt: str) -> str | None:
    """Call LLM via ollama HTTP API → cloud API → ollama CLI fallback.
    
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
        alive = req.get('http://localhost:11434/api/tags', timeout=3)
        if alive.status_code == 200:
            models = [m.get('name', '') for m in alive.json().get('models', [])]
            if model not in models:
                candidates = [m for m in models if 'glm' in m] or models
                if candidates:
                    model = candidates[0]
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '你是台股 ETF 資深分析師，輸出嚴格 JSON。'},
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
                    print(f"  [LLM reasoning] ollama HTTP OK (model={model})")
                    return content.strip()
            else:
                print(f"  [LLM reasoning] ollama HTTP {resp.status_code}: {resp.text[:200]}")
        else:
            print(f"  [LLM reasoning] ollama daemon check failed: {alive.status_code}")
    except Exception as e:
        print(f"  [LLM reasoning] ollama HTTP failed: {e}")

    # Strategy 2: OpenAI-compatible API (cloud)
    api_base = os.environ.get('LLM_API_BASE') or os.environ.get('OPENAI_API_BASE')
    api_key = os.environ.get('LLM_API_KEY') or os.environ.get('OPENAI_API_KEY') or 'dummy'

    if api_base:
        try:
            import requests as req
            url = f"{api_base.rstrip('/')}/chat/completions"
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '你是台股 ETF 資深分析師，輸出嚴格 JSON。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.3,
                'max_tokens': 300,
            }
            resp = req.post(url, json=payload, headers=headers, timeout=8)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"  [LLM reasoning] cloud API failed: {e}")

    # Strategy 3: Ollama CLI (slower, may hang in sandbox)
    if shutil.which('ollama') is not None:
        import subprocess as sp
        try:
            check = sp.run(['ollama', 'list'], capture_output=True, text=True, timeout=3)
            if check.returncode == 0:
                result = sp.run(['ollama', 'run', model, prompt], capture_output=True, text=True, timeout=15)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
        except Exception:
            print("  [LLM reasoning] ollama CLI failed, skipping")

    return None


def _parse_json_response(text: str) -> dict | None:
    """Parse JSON from LLM response."""
    cleaned = text.strip()
    if cleaned.startswith('```'):
        lines = cleaned.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        cleaned = '\n'.join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find('{')
        end = cleaned.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
    return None


def generate_llm_decision_reasoning() -> dict:
    """Main entry."""
    now = datetime.now(TW_TZ)

    # Load all sources
    event_ctx = safe_load_json(STATE / 'market_event_context.json', {})
    macro = safe_load_json(STATE / 'macro_indicators.json', {})
    calendar = safe_load_json(STATE / 'central_bank_calendar.json', {})
    news = safe_load_json(STATE / 'news_headlines.json', {})
    intel_data = safe_load_json(STATE / 'market_intelligence.json', {'intelligence': {}})
    intel = intel_data.get('intelligence', {})

    # Step 1: Generate rule-based reasoning (always available)
    rule_reasoning = _build_rule_based_reasoning(event_ctx, macro, calendar, news, intel)

    # Step 2: Try LLM enhancement
    prompt = _build_llm_prompt(rule_reasoning, event_ctx)
    llm_text = _call_llm(prompt)

    if llm_text:
        parsed = _parse_json_response(llm_text)
        if parsed and isinstance(parsed.get('market_context_summary'), str):
            reasoning = {
                'market_context_summary': parsed.get('market_context_summary', rule_reasoning['market_context_summary']),
                'risk_context_summary': parsed.get('risk_context_summary', rule_reasoning['risk_context_summary']),
                'position_context_summary': parsed.get('position_context_summary', rule_reasoning['position_context_summary']),
                'source': 'llm-enhanced-v1',
                'rule_engine_fallback': rule_reasoning,  # Keep for comparison
            }
            atomic_save_json(OUTPUT_PATH, reasoning)
            print(f"LLM_REASONING_OK: source=llm")
            print(f"  market: {reasoning['market_context_summary'][:80]}")
            print(f"  risk: {reasoning['risk_context_summary'][:80]}")
            return reasoning

    # Fallback: rule-engine reasoning
    reasoning = {
        **rule_reasoning,
        'source': 'rule-engine-v1',
    }
    atomic_save_json(OUTPUT_PATH, reasoning)
    print(f"LLM_REASONING_FALLBACK: source=rule-engine")
    print(f"  market: {reasoning['market_context_summary'][:80]}")
    print(f"  risk: {reasoning['risk_context_summary'][:80]}")
    return reasoning


if __name__ == '__main__':
    generate_llm_decision_reasoning()