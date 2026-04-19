import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class TestSyncWorldmonitorDaily(unittest.TestCase):

    def _make_mock_responses(self):
        return {
            '/api/supply-chain/v1/get-chokepoint-status': {
                # Real schema: chokepoints[] with disruptionScore/status/warRiskTier
                'chokepoints': [
                    {'id': 'hormuz_strait', 'name': 'Strait of Hormuz', 'disruptionScore': 70,
                     'status': 'red', 'warRiskTier': 'WAR_RISK_TIER_WAR_ZONE'},
                    {'id': 'taiwan_strait', 'name': 'Taiwan Strait', 'disruptionScore': 15,
                     'status': 'green', 'warRiskTier': 'WAR_RISK_TIER_ELEVATED'},
                ],
                'fetchedAt': '2026-04-19T00:00:00Z',
                'upstreamUnavailable': False,
            },
            '/api/conflict/v1/list-acled-events': {
                'global_risk_level': 'elevated',
                'active_conflicts': 3,
                'highest_severity': 'high',
            },
            '/api/supply-chain/v1/get-shipping-stress': {
                # Real schema: stressScore/stressLevel (not shipping_stress_index)
                'stressScore': 0.72,
                'stressLevel': 'moderate',
                'fetchedAt': 0,
                'upstreamUnavailable': False,
            },
            '/api/supply-chain/v1/get-critical-minerals': {
                # Real schema: minerals[] with mineral/riskRating
                'minerals': [
                    {'mineral': 'Gallium', 'riskRating': 'high', 'hhi': 8500},
                    {'mineral': 'Germanium', 'riskRating': 'critical', 'hhi': 9200},
                ],
                'fetchedAt': '2026-04-19T00:00:00Z',
                'upstreamUnavailable': False,
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
        mock_fetch.side_effect = lambda base_url, path, api_key='': responses[path]

        run_daily()

        mock_save.assert_called_once()
        saved_payload = mock_save.call_args[0][1]
        # global_stress_level derived from chokepoints (hormuz red score=70 → high)
        self.assertEqual(saved_payload['supply_chain']['global_stress_level'], 'high')
        self.assertEqual(saved_payload['geopolitical']['global_risk_level'], 'elevated')
        # shipping_stress_score from stressScore field
        self.assertAlmostEqual(saved_payload['supply_chain']['shipping_stress_score'], 0.72)
        # taiwan_strait_risk derived from WAR_RISK_TIER_ELEVATED → moderate
        self.assertEqual(saved_payload['geopolitical']['taiwan_strait_risk'], 'moderate')
        # taiwan_semiconductor_risk derived from minerals (germanium critical)
        self.assertEqual(saved_payload['supply_chain']['critical_minerals']['taiwan_semiconductor_risk'], 'critical')
        self.assertIn('updated_at', saved_payload)

    @patch('sync_worldmonitor._get_config')
    def test_daily_mode_skips_when_disabled(self, mock_config):
        from sync_worldmonitor import run_daily
        mock_config.return_value = {'base_url': 'https://test.vercel.app', 'enabled': False}
        result = run_daily()
        self.assertIsNone(result)


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


class TestCheckMajorEventWorldmonitor(unittest.TestCase):

    @patch('check_major_event_trigger.safe_load_json')
    @patch('check_major_event_trigger.atomic_save_json')
    def test_worldmonitor_l2_alert_upgrades_event_level(self, mock_save, mock_load):
        from check_major_event_trigger import classify_level_with_worldmonitor

        anomalies = []
        worldmonitor_alerts = [
            {'severity': 'L2', 'alert_type': 'supply_chain_disruption', 'title': 'test'}
        ]
        level, reason = classify_level_with_worldmonitor(anomalies, {}, {}, worldmonitor_alerts)
        self.assertEqual(level, 'L2')
        self.assertIn('worldmonitor', reason)


class TestAIDecisionBridgeWorldmonitor(unittest.TestCase):

    def test_worldmonitor_context_included_in_request(self):
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


if __name__ == '__main__':
    unittest.main()
