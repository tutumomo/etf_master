#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

SESSION_KEY = "agent:main:main"


def main() -> int:
    if len(sys.argv) < 3:
        print(json.dumps({"notified": False, "error": "missing args"}, ensure_ascii=False))
        return 1
    base_strategy = sys.argv[1]
    scenario_overlay = sys.argv[2]
    message = (
        f"[Dashboard策略同步]\n"
        f"目前投資策略已由儀表板更新為：{base_strategy}\n"
        f"情境覆蓋：{scenario_overlay}\n"
        f"請後續回覆與判斷以新策略狀態為準；此變更僅涉及策略狀態，不代表任何交易指令。"
    )
    payload = {
        "sessionKey": SESSION_KEY,
        "message": message,
        "timeoutSeconds": 3
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
