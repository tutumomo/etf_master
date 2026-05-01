from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/scripts/generate_decision_consensus.py")
spec = importlib.util.spec_from_file_location("generate_decision_consensus", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_load_etf_catalog_includes_universe_only_symbol():
    catalog = module.load_etf_catalog()

    assert "00939" in catalog["etfs"]
    assert catalog["etfs"]["00939"]["name"] == "統一台灣高息動能"


def test_strategy_alignment_uses_universe_metadata_for_income_etf():
    catalog = module.load_etf_catalog()

    aligned, message = module.check_strategy_alignment("00939", "平衡配置", catalog)

    assert aligned is True
    assert "查無標的" not in message
    assert "高股息" in message
