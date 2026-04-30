from pathlib import Path
import importlib.util


MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/report_templates.py")
spec = importlib.util.spec_from_file_location("report_templates", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_standard_report_templates_cover_morning_post_market_and_weekly():
    assert module.get_report_template("morning")["title"] == "ETF_TW 早班報告"
    assert "決策品質評分" in module.get_report_template("post_market")["sections"]
    assert "雙鏈勝率（累計）" in module.get_report_template("weekly")["sections"]


def test_section_heading_rejects_unknown_section():
    assert module.section_heading("weekly", "本週摘要") == "## 本週摘要"
    try:
        module.section_heading("weekly", "不存在")
    except ValueError as exc:
        assert "is not in template" in str(exc)
    else:
        raise AssertionError("expected ValueError")
