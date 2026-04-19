"""Tests for sync_decision_reviews.py and provenance chain_sources field."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def test_build_provenance_record_includes_chain_sources():
    """build_provenance_record() must store chain_sources when provided."""
    from provenance_logger import build_provenance_record

    request_payload = {
        'request_id': 'test-001',
        'inputs': {
            'strategy': {'base_strategy': '平衡配置', 'scenario_overlay': '無'},
            'positions': {'holdings': [], 'positions': []},
            'market_context_taiwan': {'market_regime': 'neutral', 'risk_temperature': 'normal'},
            'market_event_context': {'global_risk_level': 'low', 'defensive_bias': 'low'},
            'intraday_tape_context': {'market_bias': 'neutral'},
            'portfolio_snapshot': {'total_equity': 10000.0, 'cash': 5000.0},
            'orders_open': {'orders': []},
        }
    }
    response_payload = {
        'request_id': 'test-001',
        'decision': {'action': 'buy-preview', 'confidence': 'high', 'summary': 'test'},
        'candidate': {'symbol': '00878', 'reference_price': 20.5, 'quantity': 100},
    }
    chain_sources = {
        'rule_engine_action': 'buy',
        'rule_engine_symbol': '00878',
        'ai_bridge_action': 'preview_buy',
        'ai_bridge_symbol': '00878',
        'consensus_tier': 1,
        'consensus_resolved': 'buy',
        'strategy_aligned_rule': True,
        'strategy_aligned_ai': True,
    }

    record = build_provenance_record(
        request_payload=request_payload,
        response_payload=response_payload,
        source='test',
        chain_sources=chain_sources,
    )

    assert 'chain_sources' in record
    assert record['chain_sources']['consensus_tier'] == 1
    assert record['chain_sources']['rule_engine_symbol'] == '00878'


def test_build_provenance_record_without_chain_sources():
    """build_provenance_record() defaults chain_sources to None when not provided."""
    from provenance_logger import build_provenance_record

    request_payload = {
        'request_id': 'test-002',
        'inputs': {
            'strategy': {'base_strategy': '平衡配置', 'scenario_overlay': '無'},
            'positions': {'holdings': [], 'positions': []},
            'market_context_taiwan': {},
            'market_event_context': {},
            'intraday_tape_context': {},
            'portfolio_snapshot': {},
            'orders_open': {},
        }
    }
    response_payload = {
        'request_id': 'test-002',
        'decision': {'action': 'hold', 'confidence': 'medium', 'summary': 'test'},
        'candidate': {'symbol': None, 'reference_price': None, 'quantity': None},
    }

    record = build_provenance_record(
        request_payload=request_payload,
        response_payload=response_payload,
        source='test',
    )

    assert record['chain_sources'] is None