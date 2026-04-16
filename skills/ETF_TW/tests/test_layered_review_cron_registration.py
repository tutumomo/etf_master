from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_cron_registration.py")
spec = importlib.util.spec_from_file_location("layered_review_cron_registration", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_registration_records_creates_dedup_keys_for_each_window():
    plan = {
        'request_id': 'req-reg-001',
        'windows': [
            {'name': 'early_review', 'label': 'T+1 早期復盤', 'offset_trading_days': 1},
            {'name': 'short_review', 'label': 'T+3 短期復盤', 'offset_trading_days': 3},
            {'name': 'mid_review', 'label': 'T+10 中期復盤', 'offset_trading_days': 10},
        ],
        'binding': {'runner': 'scripts/auto_post_review_cycle.py'}
    }
    rows = module.build_registration_records(plan)
    assert len(rows) == 3
    assert rows[0]['dedupe_key'] == 'req-reg-001::early_review'
    assert rows[2]['dedupe_key'] == 'req-reg-001::mid_review'


def test_write_registration_records_writes_state_and_ledger():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        plan = {
            'request_id': 'req-reg-002',
            'windows': [
                {'name': 'early_review', 'label': 'T+1 早期復盤', 'offset_trading_days': 1},
            ],
            'binding': {'runner': 'scripts/auto_post_review_cycle.py'}
        }
        rows = module.write_registration_records(d, plan)
        assert len(rows) == 1
        state_payload = json.loads((d / 'layered_review_registrations.json').read_text(encoding='utf-8'))
        assert state_payload[0]['request_id'] == 'req-reg-002'
