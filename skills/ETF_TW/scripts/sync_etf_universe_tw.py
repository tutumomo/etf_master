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
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "etf_universe_tw.json"


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
        symbol = str(cell(row, "證券代號", "")).strip()
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "name": str(cell(row, "證券簡稱", "")).strip(),
                "issuer": str(cell(row, "發行人", "")).strip(),
                "index_name": str(cell(row, "標的指數", "")).strip(),
                "listing_date": str(cell(row, "上市日期", "")).strip(),
                "exchange": "TWSE",
                "source": "twse_etf_list",
            }
        )
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
        out.append(
            {
                "symbol": symbol,
                "name": str(row.get("stockName") or "").strip(),
                "issuer": str(row.get("issuer") or "").strip(),
                "index_name": str(row.get("indexName") or "").strip(),
                "listing_date": str(row.get("listingDate") or "").strip(),
                "exchange": "TPEx",
                "source": "tpex_etf_filter",
            }
        )
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
