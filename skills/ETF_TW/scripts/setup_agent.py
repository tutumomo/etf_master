#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parent.parent
INSTANCES_DIR = SKILL_PATH / "instances"


def check_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", int(port))) == 0


def find_available_port(start_port: int = 5055) -> int:
    port = start_port
    while check_port(port):
        port += 1
    return port


def setup_instance(agent_name: str) -> Path:
    instance_dir = INSTANCES_DIR / agent_name
    state_dir = instance_dir / "state"
    logs_dir = instance_dir / "logs"
    temp_dir = instance_dir / "temp"
    private_dir = instance_dir / "private"

    instance_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    temp_dir.mkdir(exist_ok=True)
    private_dir.mkdir(exist_ok=True)
    (instance_dir / "memory").mkdir(exist_ok=True)
    (instance_dir / "runtime").mkdir(exist_ok=True)

    config_path = instance_dir / "instance_config.json"
    current_port = 5055
    if config_path.exists():
        try:
            old_config = json.loads(config_path.read_text(encoding="utf-8"))
            current_port = int(old_config.get("port", 5055))
        except Exception:
            current_port = 5055

    suggested_port = current_port if not check_port(current_port) else find_available_port(5055)

    config = {
        "agent_id": agent_name,
        "accounts": {
            "sinopac_01": {
                "alias": "sinopac_01",
                "broker_id": "sinopac",
                "account_id": f"{agent_name}_live",
                "mode": "live",
                "credentials": {
                    "api_key": "",
                    "api_secret": ""
                }
            }
        },
        "default_account": "sinopac_01",
        "port": int(suggested_port),
        "watchlist": ["0050", "006208", "00878", "0056", "00919"]
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    trading_mode_path = state_dir / "trading_mode.json"
    if not trading_mode_path.exists():
        trading_mode_path.write_text(json.dumps({
            "effective_mode": "live-ready",
            "default_account": "sinopac_01",
            "health_check_ok": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    strategy_link = state_dir / "strategy_link.json"
    if not strategy_link.exists():
        strategy_link.write_text(json.dumps({
            "base_strategy": "核心累積",
            "scenario_overlay": "無",
            "updated_at": None,
            "source": agent_name,
            "header_format": "【策略：{base_strategy}｜覆蓋：{scenario_overlay}】",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    strategy_state = instance_dir / "strategy_state.json"
    if not strategy_state.exists():
        strategy_state.write_text(json.dumps({
            "base_strategy": "核心累積",
            "scenario_overlay": "無",
            "updated_at": None,
            "source": "setup_agent",
            "header_format": "【策略：{base_strategy}｜覆蓋：{scenario_overlay}】",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Instance ready: {instance_dir}")
    print(f"Port: {suggested_port}")
    print(f"Dashboard: http://localhost:{suggested_port}")
    print(f"Strategy link: {strategy_link}")
    return instance_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="ETF_TW Hermes instance setup tool")
    parser.add_argument("--link", help="Instance name to initialize, e.g. etf_master")
    args = parser.parse_args()

    if not args.link:
        print("Usage: python3 scripts/setup_agent.py --link <instance_id>")
        return 2

    setup_instance(args.link)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
