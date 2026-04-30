from pathlib import Path
import importlib.util


MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_phase2_pending_groups_combines_split_sell_signals():
    items = [
        {
            "id": "sig-board",
            "symbol": "006208",
            "side": "sell",
            "quantity": 15000,
            "trigger_payload": {
                "split_group_id": "sell-006208-1",
                "split_part": "primary",
                "split_total": 2,
                "split_total_quantity": 15763,
            },
        },
        {
            "id": "sig-odd",
            "symbol": "006208",
            "side": "sell",
            "quantity": 763,
            "trigger_payload": {
                "split_group_id": "sell-006208-1",
                "split_part": "secondary",
                "split_total": 2,
                "split_total_quantity": 15763,
            },
        },
    ]

    groups = module.build_phase2_pending_groups(items)

    assert len(groups) == 1
    assert groups[0]["is_split"] is True
    assert groups[0]["symbol"] == "006208"
    assert groups[0]["total_quantity"] == 15763
    assert [s["id"] for s in groups[0]["signals"]] == ["sig-board", "sig-odd"]


def test_overview_template_mentions_same_exit_plan_for_split_signals():
    template = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html").read_text(encoding="utf-8")
    assert "同一出場計畫" in template
    assert "整張 / 零股分送" in template
