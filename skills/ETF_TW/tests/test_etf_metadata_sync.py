from scripts.sync_etf_universe_tw import _parse_symbol_line, enrich_item


def test_parse_symbol_line_splits_currency_note():
    assert _parse_symbol_line("00625K(人民幣)") == ("00625K", "CNY")
    assert _parse_symbol_line("00636K(美元)") == ("00636K", "USD")
    assert _parse_symbol_line("006205(新臺幣)") == ("006205", "TWD")


def test_enrich_item_adds_basic_profile_fields():
    item = enrich_item({
        "symbol": "00679B",
        "name": "元大美債20年",
        "issuer": "元大證券投資信託股份有限公司",
        "index_name": "ICE美國政府20+年期債券指數",
        "listing_date": "2017.01.17",
        "exchange": "TPEx",
        "currency": "TWD",
        "source": "tpex_etf_filter",
    })
    assert item["issuer_short"] == "元大"
    assert item["asset_class"] == "bond"
    assert item["region"] == "US"
    assert item["yfinance_ticker"] == "00679B.TWO"
    assert "long_duration_bond" in item["strategy_tags"]
    assert "duration_risk" in item["risk_flags"]


def test_enrich_item_marks_active_etf_without_fake_currency_flag():
    item = enrich_item({
        "symbol": "00982A",
        "name": "主動群益台灣強棒",
        "issuer": "群益證券投資信託股份有限公司",
        "index_name": "",
        "listing_date": "2025.05.22",
        "exchange": "TWSE",
        "currency": "TWD",
        "source": "twse_etf_list",
    })
    assert item["index_name"] == "主動式 ETF（無追蹤指數）"
    assert "active_managed" in item["strategy_tags"]
    assert "currency_share_class" not in item["strategy_tags"]
    assert "fx_share_class" not in item["risk_flags"]
