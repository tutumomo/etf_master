#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

SESSION_KEY = "agent:main:main"


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"notified": False, "error": "missing mode arg"}, ensure_ascii=False))
        return 1
    
    mode_label = str(sys.argv[1]).upper()
    message = (
        f"[Dashboard交易模式同步]\n"
        f"目前交易主模式已由儀表板更新為：{mode_label}\n"
        f"請後續的風控判斷、下單預演與正式執行，皆以新模式狀態為準。\n"
        f"注意：此變更僅涉及模式狀態，不代表任何即時交易指令。"
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
