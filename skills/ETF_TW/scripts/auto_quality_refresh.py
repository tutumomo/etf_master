#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from ai_decision_quality_state import write_ai_decision_quality_state


def auto_refresh_quality_state(state_dir: Path):
    # Ensure decision_quality.json exists (0-100 numeric backbone)
    try:
        from score_decision_quality import main as score_main
        score_main()
    except Exception:
        # Best-effort; ai_decision_quality will fall back to heuristic.
        pass

    # Then write ai_decision_quality.json into the same state_dir
    return write_ai_decision_quality_state(state_dir)


if __name__ == '__main__':
    # Usage: auto_quality_refresh.py <state_dir>
    state_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / 'instances' / 'etf_master' / 'state')
    payload = auto_refresh_quality_state(state_dir)
    import json
    print(json.dumps(payload, ensure_ascii=False, indent=2))
