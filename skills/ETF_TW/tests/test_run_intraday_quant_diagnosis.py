import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_intraday_quant_diagnosis import build_intraday_quant_diagnosis


def _write(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_quant_diagnosis_combines_positions_and_watchlist(tmp_path):
    _write(tmp_path / "positions.json", {
        "positions": [
            {"symbol": "0050", "quantity": 1000, "average_price": 180.0},
        ],
    })
    _write(tmp_path / "watchlist.json", {
        "items": [
            {"symbol": "0050", "name": "元大台灣50", "group": "core"},
            {"symbol": "006208", "name": "富邦台50", "group": "core"},
        ],
    })
    _write(tmp_path / "market_cache.json", {
        "quotes": {
            "0050": {"current_price": 190.0, "prev_close": 188.0, "open": 189.0, "source": "test"},
            "006208": {"current_price": 100.0, "prev_close": 98.0, "open": 99.0, "source": "test"},
        },
    })
    _write(tmp_path / "intraday_tape_context.json", {
        "watchlist_signals": [
            {"symbol": "0050", "relative_strength": "strong", "tape_label": "偏多震盪"},
        ],
    })

    payload = build_intraday_quant_diagnosis(tmp_path)

    assert payload["symbol_count"] == 2
    assert payload["position_count"] == 1
    row_0050 = next(row for row in payload["rows"] if row["symbol"] == "0050")
    assert row_0050["in_position"] is True
    assert row_0050["change_pct"] == 1.06
    assert row_0050["unrealized_return_pct"] == 5.56
    row_006208 = next(row for row in payload["rows"] if row["symbol"] == "006208")
    assert row_006208["in_position"] is False


def test_quant_diagnosis_reports_missing_quotes(tmp_path):
    _write(tmp_path / "positions.json", {"positions": []})
    _write(tmp_path / "watchlist.json", {"items": [{"symbol": "00929"}]})
    _write(tmp_path / "market_cache.json", {"quotes": {}})
    _write(tmp_path / "intraday_tape_context.json", {"watchlist_signals": []})

    payload = build_intraday_quant_diagnosis(tmp_path)

    assert payload["missing_quotes"] == ["00929"]
    assert payload["rows"][0]["tape_label"] == "資料不足"
