from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

COMPLETE_TRADE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/complete_trade.py")
complete_spec = importlib.util.spec_from_file_location("complete_trade", COMPLETE_TRADE_PATH)
complete_module = importlib.util.module_from_spec(complete_spec)
complete_spec.loader.exec_module(complete_module)

POLL_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/poll_order_status.py")
poll_spec = importlib.util.spec_from_file_location("poll_order_status", POLL_PATH)
poll_module = importlib.util.module_from_spec(poll_spec)
poll_spec.loader.exec_module(poll_module)


def test_submit_row_contains_metadata_contract():
    row = complete_module.build_submit_order_row(
        order_id="43e14cbd",
        symbol="00922",
        action="buy",
        quantity=50,
        price=27.45,
        mode="live",
        account_id="sinopac_01",
        broker_id="sinopac",
        verified=True,
        broker_order_id="43e14cbd",
        broker_status="submitted",
    )
    assert row["source_type"] == "submit_verification"
    assert row["raw_status"] == "submitted"
    assert "observed_at" in row


def test_polling_row_contains_metadata_contract():
    row = poll_module.build_polling_order_row(
        order_id="43e14cbd",
        symbol="00922",
        action="buy",
        quantity=50,
        price=27.45,
        status="submitted",
    )
    assert row["source_type"] == "broker_polling"
    assert row["raw_status"] == "submitted"
    assert "observed_at" in row
