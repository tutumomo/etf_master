from pathlib import Path
import importlib.util
import json


MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/check_cron_stock_analysis_gap.py")
spec = importlib.util.spec_from_file_location("check_cron_stock_analysis_gap", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_find_live_prompt_dependencies_detects_old_script_path():
    jobs = {"jobs": [{"name": "old", "prompt": "uv run skills/stock-analysis-tw/scripts/analyze_stock.py"}]}
    assert module.find_live_prompt_dependencies(jobs) == ["old"]


def test_build_gap_report_passes_after_cutoff_when_latest_output_is_clean(tmp_path):
    (tmp_path / "cron" / "output" / "1090aafd4264").mkdir(parents=True)
    (tmp_path / "cron" / "jobs.json").write_text(json.dumps({
        "jobs": [{"name": "ETF 盤中智慧掃描", "prompt": "scripts/run_intraday_quant_diagnosis.py"}]
    }), encoding="utf-8")
    (tmp_path / "cron" / "output" / "1090aafd4264" / "2026-04-30_12-02-20.md").write_text(
        "缺口：stock-analysis-tw 腳本不存在", encoding="utf-8"
    )
    (tmp_path / "cron" / "output" / "1090aafd4264" / "2026-04-30_13-02-12.md").write_text(
        "所有同步 / 診斷 / Wiki / 決策刷新腳本完成無失敗", encoding="utf-8"
    )

    report = module.build_gap_report(
        tmp_path,
        since=module.datetime.fromisoformat("2026-04-30T13:00:00"),
    )

    assert report["ok"] is True
    assert report["recent_missing_script_count"] == 0
