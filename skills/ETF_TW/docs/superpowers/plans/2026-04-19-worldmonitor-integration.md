# WorldMonitor × ETF_TW 整合實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 整合 worldmonitor 全球風險信號進 etf_master，強化 AI 決策橋輸入視野，並在 L2/L3 事件時自動觸發保護機制。

**Architecture:** 新增 `sync_worldmonitor.py` 腳本呼叫 worldmonitor Vercel endpoints，產出 `worldmonitor_snapshot.json`（每日快照）和 `worldmonitor_alerts.jsonl`（即時警報）。現有 `check_major_event_trigger.py` 和 `ai_decision_bridge.py` 各新增一個輸入讀取路徑。Dashboard 新增全球風險面板。

**Tech Stack:** Python 3.14, requests, FastAPI, pytest, etf_core.state_io (atomic_save_json / safe_append_jsonl / safe_load_json)

**Design Spec:** `docs/superpowers/specs/2026-04-19-worldmonitor-integration-design.md`

---

## 檔案地圖

| 操作 | 路徑 | 職責 |
|------|------|------|
| 新增 | `scripts/sync_worldmonitor.py` | 呼叫 worldmonitor endpoints，雙模式（daily/watch），寫 state |
| 新增 | `tests/test_sync_worldmonitor.py` | 測試 sync_worldmonitor 所有核心邏輯 |
| 修改 | `scripts/check_major_event_trigger.py` | 新增讀取 worldmonitor_alerts.jsonl，合併事件等級 |
| 修改 | `scripts/ai_decision_bridge.py` | 新增第 13 個輸入源 worldmonitor_context |
| 修改 | `dashboard/app.py` | 新增 `/api/worldmonitor-status` endpoint |
| 修改 | `dashboard/templates/overview.html` | 新增全球風險雷達卡片 |
| 修改 | `cron/jobs.json`（profile 根目錄） | 新增兩個 cron 任務 |

**State 新增（自動由腳本建立，不需手動）：**
- `instances/etf_master/state/worldmonitor_snapshot.json`
- `instances/etf_master/state/worldmonitor_alerts.jsonl`

---

## Task 1：`sync_worldmonitor.py` 核心框架 + daily 模式

**Files:**
- Create: `scripts/sync_worldmonitor.py`
- Create: `tests/test_sync_worldmonitor.py`

- [ ] **Step 1: 寫失敗測試 — daily 模式正常寫入快照**

```python
# tests/test_sync_worldmonitor.py
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

class TestSyncWorldmonitorDaily(unittest.TestCase):

    def _make_mock_responses(self):
        """模擬 worldmonitor 四個 endpoints 的回傳"""
        return {
            '/api/supply-chain/status': {
                'global_stress_level': 'moderate',
                'chokepoints': [{'name': 'Strait of Hormuz', 'status': 'disrupted', 'severity': 3}],
            },
            '/api/conflicts/active': {
                'global_risk_level': 'elevated',
                'active_conflicts': 3,
                'highest_severity': 'high',
                'taiwan_strait_risk': 'low',
            },
            '/api/shipping/stress': {
                'shipping_stress_index': 0.72,
            },
            '/api/supply-chain/critical-minerals': {
                'taiwan_semiconductor_risk': 'elevated',
            },
        }

    @patch('sync_worldmonitor.atomic_save_json')
    @patch('sync_worldmonitor._fetch_endpoint')
    @patch('sync_worldmonitor._get_config')
    def test_daily_mode_writes_snapshot(self, mock_config, mock_fetch, mock_save):
        from sync_worldmonitor import run_daily

        mock_config.return_value = {
            'base_url': 'https://test.vercel.app',
            'enabled': True,
        }
        responses = self._make_mock_responses()
        mock_fetch.side_effect = lambda base_url, path: responses[path]

        run_daily()

        mock_save.assert_called_once()
        saved_payload = mock_save.call_args[0][1]
        self.assertEqual(saved_payload['supply_chain']['global_stress_level'], 'moderate')
        self.assertEqual(saved_payload['geopolitical']['global_risk_level'], 'elevated')
        self.assertAlmostEqual(saved_payload['supply_chain']['shipping_stress_index'], 0.72)
        self.assertIn('updated_at', saved_payload)

    @patch('sync_worldmonitor._get_config')
    def test_daily_mode_skips_when_disabled(self, mock_config):
        from sync_worldmonitor import run_daily
        mock_config.return_value = {'base_url': 'https://test.vercel.app', 'enabled': False}
        # 不應拋出任何例外，靜默退出
        result = run_daily()
        self.assertIsNone(result)
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestSyncWorldmonitorDaily -v
```

期望：`ModuleNotFoundError: No module named 'sync_worldmonitor'`

- [ ] **Step 3: 建立 `scripts/sync_worldmonitor.py` 實作 daily 模式**

```python
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
    'supply_chain_status':   '/api/supply-chain/status',
    'conflicts_active':      '/api/conflicts/active',
    'shipping_stress':       '/api/shipping/stress',
    'critical_minerals':     '/api/supply-chain/critical-minerals',
}

# 動態曝險映射關鍵字（掃描 ETF focus/index/name）
RISK_DIMENSION_KEYWORDS: dict[str, list[str]] = {
    'taiwan_strait_risk':    ['台灣', '台股', '加權', '0050', '006208', '00878', '00919'],
    'us_bond_risk':          ['美債', '公債', 'bond', '00679B', '00687B'],
    'semiconductor_supply':  ['半導體', '科技', 'semiconductor', 'philly', '00830'],
    'energy_shock':          ['能源', 'energy', '油'],
    'global_risk_high':      ['*'],
}


def _get_config() -> dict:
    """從 instance_config 讀取 worldmonitor 設定"""
    try:
        cfg = get_instance_config()
        return cfg.get('worldmonitor', {})
    except Exception:
        return {}


def _fetch_endpoint(base_url: str, path: str) -> dict:
    """呼叫單一 worldmonitor endpoint，失敗時回傳空 dict"""
    try:
        resp = requests.get(f'{base_url}{path}', timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'[sync_worldmonitor] ⚠️  endpoint {path} 失敗：{e}')
        return {}


def _compute_affected_etfs(risk_type: str, watchlist: list[dict]) -> list[str]:
    """根據 ETF 元資料動態計算受影響 ETF"""
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


def _build_snapshot(responses: dict, now_str: str) -> dict:
    """將各 endpoint 回應正規化成 snapshot 格式"""
    sc = responses.get('supply_chain_status', {})
    cf = responses.get('conflicts_active', {})
    sh = responses.get('shipping_stress', {})
    cm = responses.get('critical_minerals', {})

    return {
        'updated_at': now_str,
        'source': 'worldmonitor',
        'supply_chain': {
            'global_stress_level': sc.get('global_stress_level', 'unknown'),
            'chokepoints': sc.get('chokepoints', []),
            'shipping_stress_index': sh.get('shipping_stress_index'),
            'critical_minerals': {
                'taiwan_semiconductor_risk': cm.get('taiwan_semiconductor_risk', 'unknown'),
            },
        },
        'geopolitical': {
            'global_risk_level': cf.get('global_risk_level', 'unknown'),
            'active_conflicts': cf.get('active_conflicts', 0),
            'highest_severity': cf.get('highest_severity', 'unknown'),
            'taiwan_strait_risk': cf.get('taiwan_strait_risk', 'unknown'),
        },
        'macro': {
            'usd_index_trend': cf.get('usd_index_trend', 'unknown'),
            'energy_price_pressure': sc.get('energy_price_pressure', 'unknown'),
        },
    }


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

    responses = {}
    for key, path in ENDPOINTS.items():
        responses[key] = _fetch_endpoint(base_url, path)

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

    state_dir = get_state_dir()
    prev_snapshot = safe_load_json(state_dir / 'worldmonitor_snapshot.json', {})

    responses = {}
    for key, path in ENDPOINTS.items():
        responses[key] = _fetch_endpoint(base_url, path)

    now_str = datetime.now(TW_TZ).isoformat()
    new_snapshot = _build_snapshot(responses, now_str)

    # 載入 watchlist 以動態計算曝險
    if watchlist_items is None:
        watchlist_data = safe_load_json(state_dir / 'watchlist.json', {})
        watchlist_items = watchlist_data.get('items', [])

    alerts = _detect_alerts(prev_snapshot, new_snapshot, watchlist_items, now_str)
    for alert in alerts:
        safe_append_jsonl(state_dir / 'worldmonitor_alerts.jsonl', alert)
        print(f'[sync_worldmonitor] ⚠️  alert: {alert["severity"]} — {alert["title"]}')

    # 更新快照
    atomic_save_json(state_dir / 'worldmonitor_snapshot.json', new_snapshot)

    # L3 事件直接觸發 check_major_event_trigger
    if any(a['severity'] == 'L3' for a in alerts):
        import subprocess
        subprocess.run([
            str(ROOT / 'skills/ETF_TW/.venv/bin/python'),
            str(ROOT / 'skills/ETF_TW/scripts/check_major_event_trigger.py'),
        ], check=False)

    return None


def _detect_alerts(prev: dict, curr: dict, watchlist: list[dict], now_str: str) -> list[dict]:
    """比較前後快照，產生 alert 列表"""
    alerts = []
    severity_map = {'critical': 'L3', 'high': 'L2', 'moderate': 'L1', 'low': 'L1'}

    # 地緣政治風險升級
    prev_geo = prev.get('geopolitical', {}).get('global_risk_level', 'unknown')
    curr_geo = curr.get('geopolitical', {}).get('global_risk_level', 'unknown')
    level_rank = {'low': 0, 'moderate': 1, 'elevated': 2, 'high': 3, 'critical': 4}
    if level_rank.get(curr_geo, 0) > level_rank.get(prev_geo, 0):
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
    if level_rank.get(curr_tw, 0) > level_rank.get(prev_tw, 0):
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
    if level_rank.get(curr_sc, 0) > level_rank.get(prev_sc, 0):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='同步 worldmonitor 全球風險信號')
    parser.add_argument('--mode', choices=['daily', 'watch'], default='daily',
                        help='daily=每日快照；watch=事件監控')
    args = parser.parse_args()

    if args.mode == 'daily':
        run_daily()
    else:
        run_watch()
```

- [ ] **Step 4: 執行測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestSyncWorldmonitorDaily -v
```

期望：`2 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
git add scripts/sync_worldmonitor.py tests/test_sync_worldmonitor.py
git commit -m "feat(worldmonitor): add sync_worldmonitor.py daily mode with snapshot normalization"
```

---

## Task 2：`sync_worldmonitor.py` watch 模式測試

**Files:**
- Modify: `tests/test_sync_worldmonitor.py`

- [ ] **Step 1: 新增 watch 模式測試**

在 `tests/test_sync_worldmonitor.py` 新增以下測試類別：

```python
class TestSyncWorldmonitorWatch(unittest.TestCase):

    def _snapshot_low(self):
        return {
            'updated_at': '2026-04-19T09:00:00+08:00',
            'supply_chain': {'global_stress_level': 'low', 'chokepoints': [], 'shipping_stress_index': 0.3},
            'geopolitical': {'global_risk_level': 'low', 'active_conflicts': 1, 'highest_severity': 'low', 'taiwan_strait_risk': 'low'},
            'macro': {},
        }

    def _snapshot_elevated(self):
        return {
            'updated_at': '2026-04-19T10:00:00+08:00',
            'supply_chain': {'global_stress_level': 'high', 'chokepoints': [], 'shipping_stress_index': 0.85},
            'geopolitical': {'global_risk_level': 'elevated', 'active_conflicts': 4, 'highest_severity': 'high', 'taiwan_strait_risk': 'low'},
            'macro': {},
        }

    def test_watch_detects_geopolitical_escalation(self):
        from sync_worldmonitor import _detect_alerts
        watchlist = [
            {'symbol': '0050', 'focus': '台灣50', 'index': '加權指數', 'name': '元大台灣50'},
        ]
        alerts = _detect_alerts(self._snapshot_low(), self._snapshot_elevated(), watchlist, '2026-04-19T10:00:00+08:00')
        types = [a['alert_type'] for a in alerts]
        self.assertIn('geopolitical_escalation', types)
        geo_alert = next(a for a in alerts if a['alert_type'] == 'geopolitical_escalation')
        self.assertEqual(geo_alert['severity'], 'L2')
        self.assertIn('0050', geo_alert['affected_etfs'])

    def test_watch_detects_supply_chain_escalation(self):
        from sync_worldmonitor import _detect_alerts
        watchlist = [
            {'symbol': '00830', 'focus': '費城半導體', 'index': 'Philadelphia Semiconductor', 'name': '國泰費城半導體'},
        ]
        alerts = _detect_alerts(self._snapshot_low(), self._snapshot_elevated(), watchlist, '2026-04-19T10:00:00+08:00')
        types = [a['alert_type'] for a in alerts]
        self.assertIn('supply_chain_disruption', types)

    def test_watch_no_alert_when_no_change(self):
        from sync_worldmonitor import _detect_alerts
        alerts = _detect_alerts(self._snapshot_low(), self._snapshot_low(), [], '2026-04-19T10:00:00+08:00')
        self.assertEqual(alerts, [])

    def test_compute_affected_etfs_dynamic(self):
        from sync_worldmonitor import _compute_affected_etfs
        watchlist = [
            {'symbol': '0050', 'focus': '台灣50', 'index': '加權指數', 'name': '元大台灣50'},
            {'symbol': '00679B', 'focus': '美國公債', 'index': 'ICE US Treasury 20+', 'name': '元大美債20年'},
            {'symbol': '00830', 'focus': '費城半導體', 'index': 'Philadelphia Semiconductor', 'name': ''},
        ]
        affected = _compute_affected_etfs('us_bond_risk', watchlist)
        self.assertIn('00679B', affected)
        self.assertNotIn('0050', affected)
        self.assertNotIn('00830', affected)

    def test_global_risk_high_affects_all(self):
        from sync_worldmonitor import _compute_affected_etfs
        watchlist = [
            {'symbol': '0050', 'focus': '', 'index': '', 'name': ''},
            {'symbol': '00679B', 'focus': '', 'index': '', 'name': ''},
        ]
        affected = _compute_affected_etfs('global_risk_high', watchlist)
        self.assertIn('0050', affected)
        self.assertIn('00679B', affected)
```

- [ ] **Step 2: 執行測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestSyncWorldmonitorWatch -v
```

期望：`5 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_sync_worldmonitor.py
git commit -m "test(worldmonitor): add watch mode and dynamic ETF exposure mapping tests"
```

---

## Task 3：整合 `check_major_event_trigger.py`

**Files:**
- Modify: `scripts/check_major_event_trigger.py`
- Modify: `tests/test_sync_worldmonitor.py`（新增整合測試）

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_sync_worldmonitor.py` 新增：

```python
class TestCheckMajorEventWorldmonitor(unittest.TestCase):

    @patch('check_major_event_trigger.safe_load_json')
    @patch('check_major_event_trigger.atomic_save_json')
    def test_worldmonitor_l2_alert_upgrades_event_level(self, mock_save, mock_load):
        """worldmonitor L2 alert 應讓 combined_level 升至 L2"""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        from check_major_event_trigger import classify_level_with_worldmonitor

        anomalies = []  # 原本無事件
        worldmonitor_alerts = [
            {'severity': 'L2', 'alert_type': 'supply_chain_disruption', 'title': 'test'}
        ]
        level, reason = classify_level_with_worldmonitor(anomalies, {}, {}, worldmonitor_alerts)
        self.assertEqual(level, 'L2')
        self.assertIn('worldmonitor', reason)
```

- [ ] **Step 2: 執行確認失敗**

```bash
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestCheckMajorEventWorldmonitor -v
```

期望：`ImportError: cannot import name 'classify_level_with_worldmonitor'`

- [ ] **Step 3: 修改 `scripts/check_major_event_trigger.py`**

在現有 `classify_level()` 函數之後（約第 30 行）新增：

```python
def _load_worldmonitor_alerts(state_dir: Path) -> list[dict]:
    """讀取未超過 2 小時的 worldmonitor alerts"""
    alerts_path = state_dir / 'worldmonitor_alerts.jsonl'
    if not alerts_path.exists():
        return []
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        alerts = []
        for line in alerts_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ts_str = record.get('timestamp', '')
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    alerts.append(record)
            except Exception:
                continue
        return alerts
    except Exception:
        return []


def classify_level_with_worldmonitor(
    anomalies: list[str],
    market_cache: dict,
    market_context: dict,
    worldmonitor_alerts: list[dict] | None = None,
) -> tuple[str, str]:
    """擴充版 classify_level：合併 worldmonitor alerts"""
    base_level, base_reason = classify_level(anomalies, market_cache, market_context)

    if not worldmonitor_alerts:
        return base_level, base_reason

    level_rank = {'none': 0, 'L1': 1, 'L2': 2, 'L3': 3}
    wm_max_severity = 'none'
    wm_titles = []
    for alert in worldmonitor_alerts:
        sev = alert.get('severity', 'L1')
        if level_rank.get(sev, 0) > level_rank.get(wm_max_severity, 0):
            wm_max_severity = sev
        wm_titles.append(alert.get('title', ''))

    if level_rank.get(wm_max_severity, 0) > level_rank.get(base_level, 0):
        combined_reason = f'worldmonitor 信號升級（{wm_max_severity}）：' + '；'.join(wm_titles[:2])
        return wm_max_severity, combined_reason

    return base_level, base_reason
```

在 `main()` 函數中，找到 `classify_level(anomalies, ...)` 呼叫（約第 70 行），替換為：

```python
    worldmonitor_alerts = _load_worldmonitor_alerts(STATE)
    level, category = classify_level_with_worldmonitor(
        anomalies, market_cache, market_context, worldmonitor_alerts
    )
```

同時在檔案頂部確認已有 `import json`（現有檔案應已有）。

- [ ] **Step 4: 執行測試確認通過**

```bash
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestCheckMajorEventWorldmonitor -v
```

期望：`1 passed`

- [ ] **Step 5: 跑現有 check_major_event 相關測試確認無回歸**

```bash
.venv/bin/python -m pytest tests/ -k "major_event" -v --tb=short
```

期望：全部 pass（無新失敗）

- [ ] **Step 6: Commit**

```bash
git add scripts/check_major_event_trigger.py tests/test_sync_worldmonitor.py
git commit -m "feat(worldmonitor): integrate worldmonitor alerts into check_major_event_trigger L1/L2/L3 classification"
```

---

## Task 4：整合 `ai_decision_bridge.py`（第 13 個輸入源）

**Files:**
- Modify: `scripts/ai_decision_bridge.py`
- Modify: `tests/test_sync_worldmonitor.py`

- [ ] **Step 1: 找到 `build_ai_decision_request()` 的輸入彙整位置**

```bash
grep -n "build_ai_decision_request\|input_refs\|worldmonitor" scripts/ai_decision_bridge.py | head -20
```

記錄函數所在行號（下方步驟會用到）。

- [ ] **Step 2: 寫失敗測試**

在 `tests/test_sync_worldmonitor.py` 新增：

```python
class TestAIDecisionBridgeWorldmonitor(unittest.TestCase):

    @patch('ai_decision_bridge.safe_load_json')
    def test_worldmonitor_context_included_in_request(self, mock_load):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        from ai_decision_bridge import _build_worldmonitor_context

        snapshot = {
            'supply_chain': {'global_stress_level': 'moderate', 'shipping_stress_index': 0.72},
            'geopolitical': {'global_risk_level': 'elevated', 'taiwan_strait_risk': 'low'},
        }
        alerts = [
            {'severity': 'L2', 'alert_type': 'supply_chain_disruption',
             'title': 'test', 'affected_etfs': ['00830']},
        ]
        ctx = _build_worldmonitor_context(snapshot, alerts)
        self.assertEqual(ctx['supply_chain_stress'], 'moderate')
        self.assertEqual(ctx['geopolitical_risk'], 'elevated')
        self.assertEqual(ctx['taiwan_strait_risk'], 'low')
        self.assertEqual(ctx['active_alerts_count'], 1)
        self.assertEqual(ctx['highest_alert_severity'], 'L2')
        self.assertIn('00830', ctx['affected_etf_signals'])
```

- [ ] **Step 3: 執行確認失敗**

```bash
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestAIDecisionBridgeWorldmonitor -v
```

期望：`ImportError: cannot import name '_build_worldmonitor_context'`

- [ ] **Step 4: 修改 `scripts/ai_decision_bridge.py`**

在檔案末尾現有函數之後新增：

```python
def _build_worldmonitor_context(snapshot: dict, alerts: list[dict]) -> dict:
    """將 worldmonitor snapshot + alerts 整理成 AI 決策橋的第 13 個輸入源"""
    level_rank = {'L1': 1, 'L2': 2, 'L3': 3}
    highest = 'none'
    affected_signals: dict[str, dict] = {}

    for alert in alerts:
        sev = alert.get('severity', 'L1')
        if level_rank.get(sev, 0) > level_rank.get(highest, 0):
            highest = sev
        for etf in alert.get('affected_etfs', []):
            if etf not in affected_signals:
                affected_signals[etf] = {}
            affected_signals[etf][alert.get('alert_type', 'unknown')] = alert.get('title', '')

    sc = snapshot.get('supply_chain', {})
    geo = snapshot.get('geopolitical', {})

    return {
        'supply_chain_stress': sc.get('global_stress_level', 'unknown'),
        'geopolitical_risk': geo.get('global_risk_level', 'unknown'),
        'taiwan_strait_risk': geo.get('taiwan_strait_risk', 'unknown'),
        'active_alerts_count': len(alerts),
        'highest_alert_severity': highest,
        'affected_etf_signals': affected_signals,
    }
```

在 `build_ai_decision_request()` 函數中，找到最終 payload 組裝處，新增第 13 個輸入源：

```python
    # 第 13 個輸入源：worldmonitor 全球風險
    wm_snapshot = safe_load_json(state_dir / 'worldmonitor_snapshot.json', {})
    wm_alerts_path = state_dir / 'worldmonitor_alerts.jsonl'
    wm_alerts = []
    if wm_alerts_path.exists():
        from datetime import timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
        for line in wm_alerts_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ts = datetime.fromisoformat(record.get('timestamp', '').replace('Z', '+00:00'))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    wm_alerts.append(record)
            except Exception:
                continue
    payload['worldmonitor_context'] = _build_worldmonitor_context(wm_snapshot, wm_alerts)
```

（將此段加在 `return payload` 之前，具體行號執行 Step 1 後確認。）

- [ ] **Step 5: 執行測試確認通過**

```bash
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py::TestAIDecisionBridgeWorldmonitor -v
```

期望：`1 passed`

- [ ] **Step 6: 跑 AI decision bridge 相關測試確認無回歸**

```bash
.venv/bin/python -m pytest tests/ -k "ai_decision_bridge" -v --tb=short
```

期望：全部 pass

- [ ] **Step 7: Commit**

```bash
git add scripts/ai_decision_bridge.py tests/test_sync_worldmonitor.py
git commit -m "feat(worldmonitor): add worldmonitor_context as 13th input source in ai_decision_bridge"
```

---

## Task 5：Dashboard `/api/worldmonitor-status` endpoint + 全球風險卡片

**Files:**
- Modify: `dashboard/app.py`
- Modify: `dashboard/templates/overview.html`（若存在）

- [ ] **Step 1: 在 `dashboard/app.py` 新增 endpoint**

找到最後一個 `@app.get` 路由，在其後新增：

```python
@app.get('/api/worldmonitor-status')
def get_worldmonitor_status():
    """回傳 worldmonitor 快照摘要"""
    state_dir = get_state_dir()
    snapshot = safe_load_json(state_dir / 'worldmonitor_snapshot.json', {})

    # 讀取最近 24 小時 alerts
    alerts_path = state_dir / 'worldmonitor_alerts.jsonl'
    recent_alerts = []
    if alerts_path.exists():
        from datetime import timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for line in alerts_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ts = datetime.fromisoformat(record.get('timestamp', '').replace('Z', '+00:00'))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    recent_alerts.append(record)
            except Exception:
                continue

    highest_severity = 'none'
    level_rank = {'L1': 1, 'L2': 2, 'L3': 3}
    for a in recent_alerts:
        sev = a.get('severity', 'L1')
        if level_rank.get(sev, 0) > level_rank.get(highest_severity, 0):
            highest_severity = sev

    return {
        'ok': True,
        'updated_at': snapshot.get('updated_at'),
        'supply_chain_stress': snapshot.get('supply_chain', {}).get('global_stress_level', 'unknown'),
        'geopolitical_risk': snapshot.get('geopolitical', {}).get('global_risk_level', 'unknown'),
        'taiwan_strait_risk': snapshot.get('geopolitical', {}).get('taiwan_strait_risk', 'unknown'),
        'shipping_stress_index': snapshot.get('supply_chain', {}).get('shipping_stress_index'),
        'recent_alerts_count': len(recent_alerts),
        'highest_alert_severity': highest_severity,
    }
```

- [ ] **Step 2: 確認 endpoint 可呼叫（dashboard 若已啟動）**

```bash
curl -s http://localhost:5055/api/worldmonitor-status | python3 -m json.tool
```

若 dashboard 未啟動，跳過此步驟，在 Task 6 整合測試時驗證。

- [ ] **Step 3: 在 overview.html 新增全球風險卡片**

先確認 template 路徑：

```bash
ls ~/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/
```

找到 overview.html 後，在其他卡片的 `</div>` 之前新增：

```html
<!-- 全球風險雷達卡片 -->
<div class="card" id="worldmonitor-card">
  <div class="card-header">
    <span>🌐 全球風險雷達</span>
    <span class="badge" id="wm-updated">載入中...</span>
  </div>
  <div class="card-body">
    <table class="mini-table">
      <tr><td>供應鏈壓力</td><td id="wm-supply-chain">-</td></tr>
      <tr><td>地緣政治風險</td><td id="wm-geo-risk">-</td></tr>
      <tr><td>台海風險</td><td id="wm-taiwan-strait">-</td></tr>
      <tr><td>航運壓力指數</td><td id="wm-shipping">-</td></tr>
      <tr><td>最近警報（24h）</td><td id="wm-alerts">-</td></tr>
    </table>
  </div>
</div>

<script>
  fetch('/api/worldmonitor-status')
    .then(r => r.json())
    .then(d => {
      document.getElementById('wm-supply-chain').textContent = d.supply_chain_stress || '-';
      document.getElementById('wm-geo-risk').textContent = d.geopolitical_risk || '-';
      document.getElementById('wm-taiwan-strait').textContent = d.taiwan_strait_risk || '-';
      document.getElementById('wm-shipping').textContent = d.shipping_stress_index != null ? d.shipping_stress_index.toFixed(2) : '-';
      document.getElementById('wm-alerts').textContent = d.recent_alerts_count + ' 筆（' + (d.highest_alert_severity || 'none') + '）';
      document.getElementById('wm-updated').textContent = d.updated_at ? d.updated_at.slice(0, 16) : '未更新';
    })
    .catch(() => {
      document.getElementById('wm-updated').textContent = '載入失敗';
    });
</script>
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py dashboard/templates/overview.html
git commit -m "feat(worldmonitor): add /api/worldmonitor-status endpoint and global risk radar card"
```

---

## Task 6：設定 `instance_config.json` schema + cron 任務

**Files:**
- Modify: `instances/etf_master/instance_config.json`（新增 worldmonitor 區塊）
- Modify: `~/.hermes/profiles/etf_master/cron/jobs.json`（新增兩個任務）

> ⚠️ `instance_config.json` 是私有檔案，不能 commit。`cron/jobs.json` 在 profile 根目錄。

- [ ] **Step 1: 確認 instance_config.json 位置並新增 worldmonitor 設定**

```bash
AGENT_ID=etf_master python3 -c "
from scripts.etf_core.context import get_instance_dir
print(get_instance_dir() / 'instance_config.json')
"
```

用輸出的路徑，新增 worldmonitor 區塊（在現有 JSON 最後一個欄位後）：

```json
"worldmonitor": {
  "base_url": "https://YOUR-WORLDMONITOR-VERCEL-URL.vercel.app",
  "enabled": false,
  "watch_interval_minutes": 30
}
```

> ⚠️ 先設 `"enabled": false`，確認腳本可正確靜默退出後再改為 `true`。

- [ ] **Step 2: 驗證 disabled 時腳本靜默退出**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python scripts/sync_worldmonitor.py --mode daily
```

期望輸出：`[sync_worldmonitor] disabled，跳過`（無 exception）

- [ ] **Step 3: 在 cron/jobs.json 新增兩個任務**

讀取現有 jobs.json，在陣列末尾新增（參照現有 job 的完整結構）：

```json
{
  "id": "worldmonitor_daily",
  "name": "worldmonitor 每日快照",
  "prompt": "cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python scripts/sync_worldmonitor.py --mode daily",
  "script": "cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python scripts/sync_worldmonitor.py --mode daily",
  "schedule": {
    "kind": "cron",
    "expr": "50 7 * * 1-5",
    "display": "50 7 * * 1-5"
  },
  "enabled": false,
  "deliver": "telegram",
  "origin": {
    "platform": "telegram",
    "chat_id": "5782791568",
    "chat_name": "Tu CS",
    "thread_id": null
  }
},
{
  "id": "worldmonitor_watch",
  "name": "worldmonitor 事件巡檢",
  "prompt": "cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python scripts/sync_worldmonitor.py --mode watch",
  "script": "cd ~/.hermes/profiles/etf_master/skills/ETF_TW && AGENT_ID=etf_master .venv/bin/python scripts/sync_worldmonitor.py --mode watch",
  "schedule": {
    "kind": "cron",
    "expr": "*/30 9-13 * * 1-5",
    "display": "*/30 9-13 * * 1-5"
  },
  "enabled": false,
  "deliver": "telegram",
  "origin": {
    "platform": "telegram",
    "chat_id": "5782791568",
    "chat_name": "Tu CS",
    "thread_id": null
  }
}
```

- [ ] **Step 4: Commit cron 變更（instance_config 不 commit）**

```bash
cd ~/.hermes/profiles/etf_master
git add cron/jobs.json
git commit -m "chore(worldmonitor): add daily snapshot and watch cron tasks (disabled by default)"
```

---

## Task 7：全套測試 + 最終 push

- [ ] **Step 1: 跑完整測試套件**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m pytest tests/ -q --tb=short
```

期望：全部 pass，無新失敗。

- [ ] **Step 2: 跑 worldmonitor 專屬測試**

```bash
.venv/bin/python -m pytest tests/test_sync_worldmonitor.py -v
```

期望：所有測試 pass。

- [ ] **Step 3: 啟用 worldmonitor 整合**

確認 worldmonitor 已部署後，編輯 `instance_config.json`：
```json
"worldmonitor": {
  "base_url": "https://YOUR-ACTUAL-URL.vercel.app",
  "enabled": true,
  "watch_interval_minutes": 30
}
```

手動測試：
```bash
AGENT_ID=etf_master .venv/bin/python scripts/sync_worldmonitor.py --mode daily
cat instances/etf_master/state/worldmonitor_snapshot.json | python3 -m json.tool
```

- [ ] **Step 4: 啟用 cron 任務**

將 `cron/jobs.json` 中兩個 worldmonitor 任務的 `"enabled": false` 改為 `"enabled": true`，commit：

```bash
cd ~/.hermes/profiles/etf_master
git add cron/jobs.json
git commit -m "chore(worldmonitor): enable worldmonitor cron tasks"
```

- [ ] **Step 5: Push**

```bash
cd ~/.hermes/profiles/etf_master
git push
```

---

## 注意事項

1. **worldmonitor base_url 確認後才啟用** — `instance_config.json` 中先保持 `enabled: false`，手動 daily 模式測試成功後再啟用 cron。
2. **instance_config.json 不得 commit** — 含私有憑證，已在 .gitignore 保護。
3. **worldmonitor 連線失敗時靜默降級** — `_fetch_endpoint()` 失敗回傳 `{}`，snapshot 欄位填 `'unknown'`，不中斷現有 pipeline。
4. **ai_decision_bridge.py 修改需確認行號** — 執行 Task 4 Step 1 的 grep 後，依實際行號插入 `worldmonitor_context` 段落。
5. **跨時間因果分析** — `worldmonitor_alerts.jsonl` 為 append-only，3-6 個月後可結合 `ai_decision_outcome.jsonl` 做信號預測力回測。
