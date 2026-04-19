#!/usr/bin/env python3
"""
sync_worldmonitor.py — 從 worldmonitor 拉取全球風險信號

雙模式：
  --mode daily   每日快照（pipeline 第 11 步）
  --mode watch   事件監控（盤中每 30 分鐘）
"""
from __future__ import annotations

import sys
import json
import argparse
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from etf_core.context import get_state_dir, get_instance_config
from etf_core.state_io import atomic_save_json, safe_load_json, safe_append_jsonl

TW_TZ = ZoneInfo('Asia/Taipei')

ENDPOINTS = {
    'supply_chain_status':  '/api/supply-chain/v1/get-chokepoint-status',
    'conflicts_active':     '/api/conflict/v1/list-acled-events',
    'shipping_stress':      '/api/supply-chain/v1/get-shipping-stress',
    'critical_minerals':    '/api/supply-chain/v1/get-critical-minerals',
}

# 動態曝險映射關鍵字（掃描 ETF 的 focus/index/name/symbol）
RISK_DIMENSION_KEYWORDS: dict[str, list[str]] = {
    'taiwan_strait_risk':   ['台灣', '台股', '加權', '0050', '006208', '00878', '00919'],
    'us_bond_risk':         ['美債', '公債', 'bond', '00679B', '00687B'],
    'semiconductor_supply': ['半導體', '科技', 'semiconductor', 'philly', '00830'],
    'energy_shock':         ['能源', 'energy', '油'],
    'global_risk_high':     ['*'],
}


def _get_config() -> dict:
    """從 instance_config 讀取 worldmonitor 設定"""
    try:
        import json as _json
        cfg_path = get_instance_config()
        cfg = _json.loads(cfg_path.read_text())
        return cfg.get('worldmonitor', {})
    except Exception:
        return {}


def _fetch_endpoint(base_url: str, path: str, api_key: str = '') -> dict:
    """呼叫單一 worldmonitor endpoint，失敗時回傳空 dict"""
    try:
        headers = {
            'Origin': 'https://worldmonitor.app',
            'User-Agent': 'Mozilla/5.0 ETF-Master/1.0 (market-monitor; +https://worldmonitor.app)',
        }
        if api_key:
            headers['X-WorldMonitor-Key'] = api_key
        resp = requests.get(f'{base_url}{path}', headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'[sync_worldmonitor] ⚠️  endpoint {path} 失敗：{e}')
        return {}


def _compute_affected_etfs(risk_type: str, watchlist: list[dict]) -> list[str]:
    """根據 ETF 元資料動態計算受影響 ETF 清單"""
    keywords = RISK_DIMENSION_KEYWORDS.get(risk_type, [])
    if '*' in keywords:
        return [item.get('symbol', '') for item in watchlist if item.get('symbol')]

    affected = []
    for item in watchlist:
        symbol = item.get('symbol', '')
        searchable = ' '.join([
            symbol,
            item.get('focus', ''),
            item.get('index', ''),
            item.get('name', ''),
        ]).lower()
        if any(kw.lower() in searchable for kw in keywords):
            affected.append(symbol)
    return affected


def _derive_global_stress_level(chokepoints: list[dict]) -> str:
    """從 chokepoints disruptionScore 推算全球供應鏈壓力等級"""
    if not chokepoints:
        return 'unknown'
    scores = [cp.get('disruptionScore', 0) for cp in chokepoints]
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    red_count = sum(1 for cp in chokepoints if cp.get('status') == 'red')
    if max_score >= 70 or red_count >= 2:
        return 'critical' if max_score >= 90 else 'high'
    if max_score >= 40 or avg_score >= 20:
        return 'elevated'
    if max_score >= 20 or avg_score >= 10:
        return 'moderate'
    return 'low'


def _derive_taiwan_strait_risk(chokepoints: list[dict]) -> str:
    """從 taiwan_strait chokepoint 的 warRiskTier 推算台海風險"""
    tier_map = {
        'WAR_RISK_TIER_WAR_ZONE': 'critical',
        'WAR_RISK_TIER_CRITICAL': 'high',
        'WAR_RISK_TIER_HIGH': 'elevated',
        'WAR_RISK_TIER_ELEVATED': 'moderate',
        'WAR_RISK_TIER_NORMAL': 'low',
    }
    for cp in chokepoints:
        if cp.get('id') == 'taiwan_strait':
            tier = cp.get('warRiskTier', '')
            return tier_map.get(tier, 'unknown')
    return 'unknown'


def _derive_taiwan_semiconductor_risk(minerals: list[dict]) -> str:
    """從 critical minerals 找半導體相關礦物最高風險"""
    semi_minerals = {'silicon', 'germanium', 'gallium', 'indium', 'rare earth', 'cobalt', 'lithium'}
    risk_rank = {'critical': 4, 'high': 3, 'moderate': 2, 'elevated': 2, 'low': 1, 'unknown': 0}
    highest = 'unknown'
    for m in minerals:
        name = m.get('mineral', '').lower()
        if any(s in name for s in semi_minerals):
            risk = m.get('riskRating', 'unknown').lower()
            if risk_rank.get(risk, 0) > risk_rank.get(highest, 0):
                highest = risk
    return highest if highest != 'unknown' else 'low'


def _build_snapshot(responses: dict, now_str: str) -> dict:
    """將各 endpoint 回應正規化成 snapshot 格式"""
    sc = responses.get('supply_chain_status', {})
    cf = responses.get('conflicts_active', {})
    sh = responses.get('shipping_stress', {})
    cm = responses.get('critical_minerals', {})

    chokepoints = sc.get('chokepoints', [])
    minerals = cm.get('minerals', [])

    # 從 chokepoints 推算（API 無 global_stress_level 欄位）
    global_stress_level = _derive_global_stress_level(chokepoints)
    taiwan_strait_risk = _derive_taiwan_strait_risk(chokepoints)

    # shipping-stress API 欄位名稱是 stressLevel / stressScore
    shipping_stress_level = sh.get('stressLevel', 'unknown')
    shipping_stress_score = sh.get('stressScore')

    # conflict API 可能為空（需 ACLED key），fallback 到 chokepoint 推算
    global_risk_level = cf.get('global_risk_level', 'unknown')
    if global_risk_level == 'unknown' and chokepoints:
        global_risk_level = global_stress_level  # 最佳 fallback

    return {
        'updated_at': now_str,
        'source': 'worldmonitor',
        'supply_chain': {
            'global_stress_level': global_stress_level,
            'chokepoints': chokepoints,
            'shipping_stress_level': shipping_stress_level,
            'shipping_stress_score': shipping_stress_score,
            'critical_minerals': {
                'taiwan_semiconductor_risk': _derive_taiwan_semiconductor_risk(minerals),
            },
        },
        'geopolitical': {
            'global_risk_level': global_risk_level,
            'active_conflicts': cf.get('active_conflicts', 0),
            'highest_severity': cf.get('highest_severity', 'unknown'),
            'taiwan_strait_risk': taiwan_strait_risk,
        },
        'macro': {
            'usd_index_trend': cf.get('usd_index_trend', 'unknown'),
            'energy_price_pressure': sc.get('energy_price_pressure', 'unknown'),
        },
    }


def _detect_alerts(prev: dict, curr: dict, watchlist: list[dict], now_str: str) -> list[dict]:
    """比較前後快照，產生 alert 列表（僅在風險升級時觸發）"""
    alerts = []
    level_rank = {'unknown': -1, 'low': 0, 'moderate': 1, 'elevated': 2, 'high': 3, 'critical': 4}

    # 地緣政治風險升級
    prev_geo = prev.get('geopolitical', {}).get('global_risk_level', 'unknown')
    curr_geo = curr.get('geopolitical', {}).get('global_risk_level', 'unknown')
    if level_rank.get(curr_geo, -1) > level_rank.get(prev_geo, -1):
        severity = 'L3' if curr_geo == 'critical' else 'L2'
        alerts.append({
            'timestamp': now_str,
            'alert_type': 'geopolitical_escalation',
            'severity': severity,
            'title': f'全球地緣政治風險升級：{prev_geo} → {curr_geo}',
            'affected_etfs': _compute_affected_etfs('global_risk_high', watchlist),
            'action_hint': 'pause_auto_trade' if severity == 'L3' else 'reduce_confidence',
            'raw_source': 'worldmonitor/conflicts',
        })

    # 台海風險升級
    prev_tw = prev.get('geopolitical', {}).get('taiwan_strait_risk', 'unknown')
    curr_tw = curr.get('geopolitical', {}).get('taiwan_strait_risk', 'unknown')
    if level_rank.get(curr_tw, -1) > level_rank.get(prev_tw, -1):
        alerts.append({
            'timestamp': now_str,
            'alert_type': 'taiwan_strait_escalation',
            'severity': 'L3',
            'title': f'台海風險升級：{prev_tw} → {curr_tw}',
            'affected_etfs': _compute_affected_etfs('taiwan_strait_risk', watchlist),
            'action_hint': 'pause_auto_trade',
            'raw_source': 'worldmonitor/conflicts',
        })

    # 供應鏈壓力升級
    prev_sc = prev.get('supply_chain', {}).get('global_stress_level', 'unknown')
    curr_sc = curr.get('supply_chain', {}).get('global_stress_level', 'unknown')
    if level_rank.get(curr_sc, -1) > level_rank.get(prev_sc, -1):
        severity = 'L3' if curr_sc == 'critical' else 'L2'
        alerts.append({
            'timestamp': now_str,
            'alert_type': 'supply_chain_disruption',
            'severity': severity,
            'title': f'供應鏈壓力升級：{prev_sc} → {curr_sc}',
            'affected_etfs': _compute_affected_etfs('semiconductor_supply', watchlist),
            'action_hint': 'pause_auto_trade' if severity == 'L3' else 'reduce_confidence',
            'raw_source': 'worldmonitor/supply-chain',
        })

    return alerts


def run_daily() -> None:
    """每日模式：拉取快照並寫入 state"""
    cfg = _get_config()
    if not cfg.get('enabled', False):
        print('[sync_worldmonitor] disabled，跳過')
        return None

    base_url = cfg.get('base_url', '').rstrip('/')
    if not base_url:
        print('[sync_worldmonitor] 未設定 base_url，跳過')
        return None

    api_key = cfg.get('api_key', '')
    responses = {}
    for key, path in ENDPOINTS.items():
        responses[key] = _fetch_endpoint(base_url, path, api_key)

    now_str = datetime.now(TW_TZ).isoformat()
    snapshot = _build_snapshot(responses, now_str)

    state_dir = get_state_dir()
    atomic_save_json(state_dir / 'worldmonitor_snapshot.json', snapshot)
    print(f'[sync_worldmonitor] ✓ 每日快照已更新：{now_str}')
    return None


def run_watch(watchlist_items: list[dict] | None = None) -> None:
    """Watch 模式：偵測新 L2/L3 事件，append alerts"""
    cfg = _get_config()
    if not cfg.get('enabled', False):
        return None

    base_url = cfg.get('base_url', '').rstrip('/')
    if not base_url:
        return None

    api_key = cfg.get('api_key', '')
    state_dir = get_state_dir()
    prev_snapshot = safe_load_json(state_dir / 'worldmonitor_snapshot.json', {})

    responses = {}
    for key, path in ENDPOINTS.items():
        responses[key] = _fetch_endpoint(base_url, path, api_key)

    now_str = datetime.now(TW_TZ).isoformat()
    new_snapshot = _build_snapshot(responses, now_str)

    if watchlist_items is None:
        watchlist_data = safe_load_json(state_dir / 'watchlist.json', {})
        watchlist_items = watchlist_data.get('items', [])

    alerts = _detect_alerts(prev_snapshot, new_snapshot, watchlist_items, now_str)
    for alert in alerts:
        safe_append_jsonl(state_dir / 'worldmonitor_alerts.jsonl', alert)
        print(f'[sync_worldmonitor] ⚠️  alert: {alert["severity"]} — {alert["title"]}')

    atomic_save_json(state_dir / 'worldmonitor_snapshot.json', new_snapshot)

    if any(a['severity'] == 'L3' for a in alerts):
        import subprocess
        venv_python = ROOT / '.venv' / 'bin' / 'python3'
        trigger_script = ROOT / 'scripts' / 'check_major_event_trigger.py'
        if not venv_python.exists():
            venv_python = Path(sys.executable)
        subprocess.run([str(venv_python), str(trigger_script)], cwd=str(ROOT), check=False)

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='同步 worldmonitor 全球風險信號')
    parser.add_argument('--mode', choices=['daily', 'watch'], default='daily',
                        help='daily=每日快照；watch=事件監控')
    args = parser.parse_args()

    if args.mode == 'daily':
        run_daily()
    else:
        run_watch()
