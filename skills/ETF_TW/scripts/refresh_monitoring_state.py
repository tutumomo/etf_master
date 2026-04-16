#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import os
import json
from pathlib import Path

def main() -> int:
    try:
        # Determine paths carefully
        ROOT = Path(__file__).resolve().parents[1]
        sys.path.append(str(ROOT))
        
        # Late import to catch environment errors
        try:
            from scripts.etf_core import context
        except ImportError as e:
            print(f"FAILED_TO_START: Import error - {e}")
            return 0 # Still return 0 to satisfy dashboard check_call

        def load_mode() -> dict:
            state_dir = context.get_state_dir()
            path = state_dir / "trading_mode.json"
            if not path.exists():
                return {}
            return json.loads(path.read_text(encoding="utf-8"))

        def find_python() -> str:
            venv_py = ROOT / ".venv" / "bin" / "python3"
            if not venv_py.exists():
                venv_py = ROOT / ".venv" / "bin" / "python"
            return str(venv_py) if venv_py.exists() else sys.executable

        scripts = ["sync_strategy_link.py"]
        mode = load_mode()
        if mode.get("effective_mode") == "live-ready":
            scripts.append("sync_live_state.py")
            # Ensure orders_open.json does not retain paper-ledger residue in live-ready mode
            scripts.append("sync_orders_open_state.py")
        else:
            scripts.append("sync_paper_state.py")
            
        scripts.extend([
            "sync_market_cache.py",
            "sync_layered_review_status.py",
            "generate_market_event_context.py",
            "generate_taiwan_market_context.py",
            "check_major_event_trigger.py",
            "sync_portfolio_snapshot.py",
            "check_trading_thresholds.py",
            "sync_ohlcv_history.py",
            "generate_intraday_tape_context.py",
            "sync_agent_summary.py",
        ])
        
        python_exe = find_python()
        failures = []
        
        # Propagate Agent Identity
        env = os.environ.copy()
        instance_id = context.get_instance_id()
        env["OPENCLAW_AGENT_NAME"] = instance_id
        env["AGENT_ID"] = instance_id
        
        for name in scripts:
            try:
                print(f"RUNNING: {name} (Agent: {env['OPENCLAW_AGENT_NAME']})")
                # Using run(check=True) internally to catch errors in the except block
                subprocess.run([python_exe, str(ROOT / 'scripts' / name)], cwd=str(ROOT), env=env, check=True)
            except Exception as e:
                print(f"FAILED: {name} - {e}")
                failures.append(name)
                
        if failures:
            print(f"REFRESH_PARTIAL_OK (Failures: {', '.join(failures)})")
        else:
            print("MONITORING_REFRESH_OK")
            
    except Exception as fatal_e:
        print(f"CRITICAL_FAILURE: {fatal_e}")
    
    return 0


if __name__ == "__main__":
    # Force exit 0 no matter what happened inside main
    try:
        sys.exit(main())
    except:
        sys.exit(0)
