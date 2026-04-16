from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_strategy_link.py")
spec = importlib.util.spec_from_file_location("sync_strategy_link", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_strategy_payload_maps_strategy_state():
    payload = module.build_strategy_payload(
        {"base_strategy": "平衡配置", "scenario_overlay": "無", "updated_at": "x"}
    )
    assert payload["base_strategy"] == "平衡配置"
    assert payload["scenario_overlay"] == "無"
    assert payload["source"] == "etf_master"
