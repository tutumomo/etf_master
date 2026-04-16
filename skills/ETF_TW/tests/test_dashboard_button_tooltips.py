from pathlib import Path


def test_overview_template_contains_tooltips_for_review_and_outcome_buttons():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'title="代表你已人工看過這筆 AI 建議，並認為目前方向可接受。"' in text
    assert 'title="代表這筆 AI 建議已被新版建議或新資訊取代，不應再作為當前主建議。"' in text
    assert 'title="代表你先把這筆建議列入後續追蹤，結果尚未定案。"' in text
    assert 'title="代表你已經對這筆建議的後續結果做完一次人工評價。"' in text
