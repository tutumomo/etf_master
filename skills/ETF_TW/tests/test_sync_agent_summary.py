from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_agent_summary.py")
spec = importlib.util.spec_from_file_location("sync_agent_summary", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_strategy_header():
    assert module.build_strategy_header({'base_strategy':'平衡配置','scenario_overlay':'無'}) == '[目前投資策略:平衡配置, 情境覆蓋:無]'


def test_mode_brief_format_example():
    payload = {
        "effective_mode": "live-ready",
        "data_source": "live_broker",
    }
    mode_label = (payload.get("effective_mode") or "unknown").upper()
    data_source = payload.get("data_source") or "unknown"
    assert f"目前模式 {mode_label}，資料來源 {data_source}。" == "目前模式 LIVE-READY，資料來源 live_broker。"
