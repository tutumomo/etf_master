from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_schedule_plan.py")
spec = importlib.util.spec_from_file_location("layered_review_schedule_plan", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_layered_review_schedule_plan_contains_windows_and_binding_fields():
    plan = module.build_layered_review_schedule_plan(request_id='req-plan-001')
    assert plan['request_id'] == 'req-plan-001'
    assert len(plan['windows']) == 3
    assert plan['windows'][0]['name'] == 'early_review'
    assert 'binding' in plan
    assert plan['binding']['runner'] == 'scripts/auto_post_review_cycle.py'
