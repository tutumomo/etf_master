#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "broker_registry.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    if not path.exists():
        return {"brokers": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def build_broker_readiness(broker_id: str, broker_info: dict, adapter_config: dict | None = None) -> dict[str, Any]:
    adapter_config = adapter_config or {}
    if broker_id == "cathay":
        try:
            from adapters.cathay_adapter import build_cathay_readiness
        except ImportError:
            from scripts.adapters.cathay_adapter import build_cathay_readiness
        adapter_ready = build_cathay_readiness(adapter_config)
    else:
        adapter_ready = {
            "broker_id": broker_id,
            "ready": bool(broker_info.get("api_available")),
            "missing": [] if broker_info.get("api_available") else ["api_available"],
            "live_enabled": bool(broker_info.get("supports_live")),
            "reason": broker_info.get("notes", ""),
        }

    registry_live = bool(broker_info.get("supports_live"))
    registry_sandbox = bool(broker_info.get("supports_sandbox"))
    return {
        "broker_id": broker_id,
        "name": broker_info.get("name"),
        "api_available": bool(broker_info.get("api_available")),
        "supports_sandbox": registry_sandbox,
        "supports_live": registry_live,
        "adapter_ready": bool(adapter_ready.get("ready")),
        "live_ready": registry_live and bool(adapter_ready.get("ready")) and bool(adapter_ready.get("live_enabled")),
        "missing": adapter_ready.get("missing") or [],
        "reason": adapter_ready.get("reason") or broker_info.get("notes", ""),
    }


def build_readiness_report(registry: dict | None = None, adapter_configs: dict | None = None) -> dict:
    registry = registry or load_registry()
    adapter_configs = adapter_configs or {}
    brokers = registry.get("brokers") or {}
    rows = [
        build_broker_readiness(broker_id, info, adapter_configs.get(broker_id) or {})
        for broker_id, info in sorted(brokers.items())
    ]
    return {
        "ok": all(row["live_ready"] or not row["supports_live"] for row in rows),
        "brokers": rows,
        "source": "broker_readiness",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect broker adapter readiness.")
    parser.add_argument("--broker", help="Filter by broker id")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_readiness_report()
    rows = [row for row in report["brokers"] if not args.broker or row["broker_id"] == args.broker]

    if args.json:
        print(json.dumps({**report, "brokers": rows}, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            status = "LIVE-READY" if row["live_ready"] else "NOT-LIVE-READY"
            print(f"{row['broker_id']}: {status} | missing={','.join(row['missing']) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
