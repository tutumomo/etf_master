#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "etf_universe_tw.json"
CURATED_PATH = ROOT / "data" / "etfs.json"
WIKI_ENTITIES_DIR = ROOT.parents[1] / "wiki" / "entities"
OUT_PATH = ROOT / "data" / "etf_metadata_audit.json"

CORE_FIELDS = [
    "symbol",
    "name",
    "issuer",
    "issuer_short",
    "index_name",
    "listing_date",
    "exchange",
    "currency",
    "yfinance_ticker",
]

DERIVED_FIELDS = [
    "asset_class",
    "region",
    "strategy_tags",
    "risk_flags",
]

CURATED_FIELDS = [
    "category",
    "expense_ratio",
    "dividend_frequency",
    "inception_date",
    "aum",
    "description",
    "risk_level",
    "suitable_for",
]


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _present(value) -> bool:
    return value not in ("", None, [], {})


def _field_complete(item: dict, field: str) -> bool:
    if field in {"strategy_tags", "risk_flags"}:
        return field in item and isinstance(item.get(field), list)
    return _present(item.get(field))


def _coverage(items: dict[str, dict], fields: list[str]) -> dict[str, dict]:
    total = len(items)
    out = {}
    for field in fields:
        count = sum(1 for item in items.values() if _field_complete(item, field))
        out[field] = {
            "count": count,
            "total": total,
            "pct": round((count / total * 100.0) if total else 0.0, 2),
        }
    return out


def _wiki_symbols() -> set[str]:
    if not WIKI_ENTITIES_DIR.exists():
        return set()
    out: set[str] = set()
    for path in WIKI_ENTITIES_DIR.glob("*.md"):
        stem = path.stem
        symbol = stem.split("-", 1)[0].upper()
        if symbol and symbol[0].isdigit():
            out.add(symbol)
    return out


def build_audit() -> dict:
    universe_payload = _load_json(UNIVERSE_PATH)
    curated_payload = _load_json(CURATED_PATH)
    universe = universe_payload.get("etfs") or {}
    curated = curated_payload.get("etfs") or {}
    wiki_symbols = _wiki_symbols()

    malformed_symbols = [
        sym for sym in universe
        if "<" in sym or ">" in sym or "(" in sym or ")" in sym or "\n" in sym
    ]
    duplicate_symbol_mismatch = [
        sym for sym, item in universe.items()
        if str(item.get("symbol") or "").upper() != sym.upper()
    ]
    missing_curated = sorted(set(universe) - set(curated))
    stale_curated = sorted(set(curated) - set(universe))
    missing_wiki = sorted(set(universe) - wiki_symbols)

    by_exchange = Counter(str(item.get("exchange") or "unknown") for item in universe.values())
    by_asset_class = Counter(str(item.get("asset_class") or "unknown") for item in universe.values())
    by_region = Counter(str(item.get("region") or "unknown") for item in universe.values())
    by_issuer = Counter(str(item.get("issuer_short") or item.get("issuer") or "unknown") for item in universe.values())

    complete_core = sum(
        1 for item in universe.values()
        if all(_field_complete(item, field) for field in CORE_FIELDS)
    )
    complete_with_derived = sum(
        1 for item in universe.values()
        if all(_field_complete(item, field) for field in CORE_FIELDS + DERIVED_FIELDS)
    )
    complete_curated = sum(
        1 for item in curated.values()
        if all(_field_complete(item, field) for field in CURATED_FIELDS)
    )

    total = len(universe)
    return {
        "generated_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
        "universe_meta": universe_payload.get("meta") or {},
        "summary": {
            "universe_count": total,
            "curated_count": len(curated),
            "wiki_entity_count": len(wiki_symbols & set(universe)),
            "core_complete_count": complete_core,
            "core_complete_pct": round((complete_core / total * 100.0) if total else 0.0, 2),
            "core_plus_derived_complete_count": complete_with_derived,
            "core_plus_derived_complete_pct": round((complete_with_derived / total * 100.0) if total else 0.0, 2),
            "curated_complete_count": complete_curated,
            "curated_complete_pct": round((complete_curated / len(curated) * 100.0) if curated else 0.0, 2),
        },
        "coverage": {
            "core": _coverage(universe, CORE_FIELDS),
            "derived": _coverage(universe, DERIVED_FIELDS),
            "curated": _coverage(curated, CURATED_FIELDS),
        },
        "distribution": {
            "exchange": dict(sorted(by_exchange.items())),
            "asset_class": dict(sorted(by_asset_class.items())),
            "region": dict(sorted(by_region.items())),
            "issuer_top20": dict(by_issuer.most_common(20)),
        },
        "issues": {
            "malformed_symbols": malformed_symbols,
            "symbol_key_mismatches": duplicate_symbol_mismatch,
            "curated_missing_count": len(missing_curated),
            "curated_missing_sample": missing_curated[:50],
            "curated_stale": stale_curated,
            "wiki_missing_count": len(missing_wiki),
            "wiki_missing_sample": missing_wiki[:50],
        },
        "recommendations": [
            "Use data/etf_universe_tw.json as the broad tradable-universe truth source.",
            "Keep data/etfs.json as a high-touch curated subset for dashboard explanations, not as a full-market catalog.",
            "Prioritize curated depth for watchlist/holdings first: expense_ratio, dividend_frequency, risk_level, and description.",
            "Generate wiki entity pages only for holdings/watchlist/core ETFs; full-market wiki for every ETF is optional and noisy.",
        ],
    }


def main() -> int:
    audit = build_audit()
    OUT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ETF_METADATA_AUDIT_OK")
    print(json.dumps(audit["summary"], ensure_ascii=False, indent=2))
    issues = audit["issues"]
    print(json.dumps({
        "malformed_symbols": len(issues["malformed_symbols"]),
        "curated_missing_count": issues["curated_missing_count"],
        "wiki_missing_count": issues["wiki_missing_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
