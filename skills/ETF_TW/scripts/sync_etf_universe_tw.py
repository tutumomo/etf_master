#!/usr/bin/env python3
from __future__ import annotations
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

"""Sync Taiwan ETF universe into a local JSON file.

Sources (public, official):
- TWSE listed ETFs: https://www.twse.com.tw/rwd/zh/ETF/list?response=json
- TPEx ETFs (ETF info center API): https://info.tpex.org.tw/api/etfFilter (POST)

Output:
- data/etf_universe_tw.json

Notes:
- This file represents the *tradable universe* for validation (what exists on exchange).
- Auto-trading whitelist is a separate control and should remain strict.
"""

import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "etf_universe_tw.json"


def _clean_cell(value: object) -> str:
    text = "" if value is None else str(value)
    text = unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _split_cell(value: object) -> list[str]:
    text = _clean_cell(value)
    if not text:
        return []
    return [part.strip() for part in text.splitlines() if part.strip()]


def _pick(parts: list[str], idx: int) -> str:
    if not parts:
        return ""
    if idx < len(parts):
        return parts[idx]
    return parts[0]


def _parse_symbol_line(line: str) -> tuple[str, str | None]:
    clean = _clean_cell(line)
    match = re.match(r"^([0-9A-Z]+)(?:\(([^)]+)\))?$", clean, flags=re.IGNORECASE)
    if not match:
        return clean, None
    symbol = match.group(1).upper()
    note = match.group(2)
    currency = None
    if note:
        if "人民幣" in note:
            currency = "CNY"
        elif "美元" in note:
            currency = "USD"
        elif "新臺幣" in note or "新台幣" in note:
            currency = "TWD"
    return symbol, currency


def _issuer_short(issuer: str) -> str:
    mapping = {
        "元大": "元大",
        "富邦": "富邦",
        "國泰": "國泰",
        "復華": "復華",
        "群益": "群益",
        "兆豐": "兆豐",
        "永豐": "永豐",
        "台新": "台新",
        "街口": "街口",
        "中信": "中信",
        "凱基": "凱基",
        "第一金": "第一金",
        "統一": "統一",
        "野村": "野村",
        "新光": "新光",
        "大華銀": "大華銀",
    }
    for key, short in mapping.items():
        if key in issuer:
            return short
    return issuer[:4] if issuer else ""


def _classify_profile(symbol: str, name: str, index_name: str, exchange: str, currency: str | None) -> dict:
    text = f"{symbol} {name} {index_name}".lower()
    zh = f"{symbol} {name} {index_name}"

    if any(k in zh for k in ("債", "公債", "公司債", "投資等級", "高收益")):
        asset_class = "bond"
    elif any(k in zh for k in ("黃金", "原油", "黃豆", "商品")) or "gsci" in text:
        asset_class = "commodity"
    elif any(k in zh for k in ("美元", "日圓", "人民幣")) and any(k in zh for k in ("期貨", "指數")):
        asset_class = "currency"
    elif any(k in zh for k in ("不動產", "REIT")) or "reit" in text:
        asset_class = "real_estate"
    else:
        asset_class = "equity"

    if any(k in zh for k in ("臺灣", "台灣", "臺指", "台指", "加權", "半導體", "高股息", "藍籌")):
        region = "Taiwan"
    elif any(k in zh for k in ("美國", "標普", "那斯達克", "道瓊", "費城", "NASDAQ", "S&P")):
        region = "US"
    elif any(k in zh for k in ("中國", "滬深", "上証", "上證", "恒生", "A50", "香港")):
        region = "China/HK"
    elif any(k in zh for k in ("日本", "日經", "東証")):
        region = "Japan"
    elif "印度" in zh or "NIFTY" in zh:
        region = "India"
    elif any(k in zh for k in ("歐洲", "STOXX", "EURO")):
        region = "Europe"
    elif any(k in zh for k in ("新興市場", "全球")):
        region = "Global/Emerging"
    else:
        region = "Other"

    tags: list[str] = []
    risk_flags: list[str] = []
    is_active = "主動" in zh
    if is_active:
        tags.append("active_managed")
    if any(k in zh for k in ("正向2倍", "兩倍", "槓桿")) or "2x" in text:
        tags.append("leveraged")
        risk_flags.append("leveraged_etf")
    if any(k in zh for k in ("反向", "短倉", "Inversed", "Inverse")):
        tags.append("inverse")
        risk_flags.append("inverse_etf")
    if any(k in zh for k in ("高股息", "高息", "股利", "收益")):
        tags.append("income")
    if any(k in zh for k in ("低波", "低波動")):
        tags.append("low_volatility")
    if any(k in zh for k in ("永續", "ESG", "公司治理")):
        tags.append("esg")
    if any(k in zh for k in ("半導體", "科技", "生技", "金融", "電動車", "航太", "AI", "不動產")):
        tags.append("sector_theme")
        risk_flags.append("sector_concentration")
    if asset_class == "bond" and any(k in zh for k in ("20年", "20+")):
        tags.append("long_duration_bond")
        risk_flags.append("duration_risk")
    if asset_class == "commodity":
        tags.append("commodity")
        risk_flags.append("commodity_futures_risk")
    if currency and currency != "TWD" or symbol.endswith("K"):
        tags.append("currency_share_class")
        risk_flags.append("fx_share_class")
    if region == "China/HK":
        risk_flags.append("china_hk_policy_risk")

    return {
        "issuer_short": _issuer_short(name) or _issuer_short(index_name),
        "asset_class": asset_class,
        "region": region,
        "strategy_tags": sorted(set(tags)),
        "risk_flags": sorted(set(risk_flags)),
        "currency": currency or ("CNY" if symbol.endswith("K") else "TWD"),
        "yfinance_ticker": f"{symbol}.{'TW' if exchange == 'TWSE' else 'TWO'}",
    }


def enrich_item(item: dict) -> dict:
    enriched = dict(item)
    if not enriched.get("index_name") and "主動" in str(enriched.get("name") or ""):
        enriched["index_name"] = "主動式 ETF（無追蹤指數）"
    profile = _classify_profile(
        str(enriched.get("symbol") or ""),
        str(enriched.get("name") or ""),
        str(enriched.get("index_name") or ""),
        str(enriched.get("exchange") or ""),
        enriched.get("currency"),
    )
    if enriched.get("issuer"):
        profile["issuer_short"] = _issuer_short(str(enriched.get("issuer")))
    enriched.update(profile)
    return enriched


def _http_json(url: str, *, method: str = "GET", data: dict | None = None, timeout: int = 20) -> dict:
    """Fetch JSON with a robust strategy.

    Rationale:
    - Some macOS Python builds (e.g., python@3.14 from Homebrew) may hit SSL cert verification
      issues on certain hosts. We prefer curl for robustness.
    """

    # Prefer curl to avoid Python SSL issues.
    cmd = ["curl", "-fsSL", "--max-time", str(timeout), "-H", "Accept: application/json,text/plain,*/*", "-H", "User-Agent: ETF_TW/1.0 (+https://github.com/tutumomo/ETF_TW)"]
    if method.upper() == "POST":
        cmd += ["-X", "POST"]
        if data is not None:
            cmd += ["--data", urllib.parse.urlencode(data)]
        else:
            cmd += ["--data", ""]
    cmd += [url]

    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "ignore")
        return json.loads(raw)
    except Exception:
        # Fallback to urllib if curl is unavailable.
        headers = {
            "User-Agent": "ETF_TW/1.0 (+https://github.com/tutumomo/ETF_TW)",
            "Accept": "application/json,text/plain,*/*",
        }
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "ignore")
        return json.loads(raw)


def fetch_twse() -> list[dict]:
    url = "https://www.twse.com.tw/rwd/zh/ETF/list?response=json"
    payload = _http_json(url)
    if payload.get("stat") != "OK":
        raise RuntimeError(f"TWSE ETF list stat != OK: {payload.get('stat')}")

    fields = payload.get("fields") or []
    data = payload.get("data") or []

    idx = {name: i for i, name in enumerate(fields)}
    def cell(row, name, default=None):
        i = idx.get(name)
        if i is None:
            return default
        try:
            return row[i]
        except Exception:
            return default

    out = []
    for row in data:
        symbol_lines = _split_cell(cell(row, "證券代號", ""))
        if not symbol_lines:
            continue
        name_lines = _split_cell(cell(row, "證券簡稱", ""))
        listing_lines = _split_cell(cell(row, "上市日期", ""))
        issuer = _clean_cell(cell(row, "發行人", ""))
        index_name = _clean_cell(cell(row, "標的指數", ""))

        for i, raw_symbol in enumerate(symbol_lines):
            symbol, currency = _parse_symbol_line(raw_symbol)
            if not symbol:
                continue
            out.append(enrich_item({
                "symbol": symbol,
                "name": _pick(name_lines, i),
                "issuer": issuer,
                "index_name": index_name,
                "listing_date": _pick(listing_lines, i),
                "exchange": "TWSE",
                "currency": currency or "TWD",
                "raw_symbol": raw_symbol,
                "source": "twse_etf_list",
            }))
    return out


def fetch_tpex() -> list[dict]:
    # Endpoint used by TPEx ETF info center filter page.
    url = "https://info.tpex.org.tw/api/etfFilter"
    payload = _http_json(url, method="POST", data={})
    if payload.get("status") != "success":
        raise RuntimeError(f"TPEx etfFilter status != success: {payload.get('status')}")

    data = payload.get("data") or []
    out = []
    for row in data:
        symbol = str(row.get("stockNo") or "").strip()
        if not symbol:
            continue
        out.append(enrich_item({
            "symbol": symbol,
            "name": _clean_cell(row.get("stockName")),
            "issuer": _clean_cell(row.get("issuer")),
            "index_name": _clean_cell(row.get("indexName")),
            "listing_date": _clean_cell(row.get("listingDate")),
            "exchange": "TPEx",
            "currency": "TWD",
            "source": "tpex_etf_filter",
        }))
    return out


def main() -> int:
    twse = fetch_twse()
    tpex = fetch_tpex()

    merged: dict[str, dict] = {}
    for item in twse + tpex:
        sym = item["symbol"]
        merged[sym] = item

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "meta": {
            "version": "1.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "counts": {
                "twse": len(twse),
                "tpex": len(tpex),
                "merged": len(merged),
            },
            "sources": [
                "https://www.twse.com.tw/rwd/zh/ETF/list?response=json",
                "https://info.tpex.org.tw/api/etfFilter",
            ],
        },
        "etfs": merged,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("ETF_UNIVERSE_SYNC_OK")
    print(json.dumps(out["meta"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
