#!/usr/bin/env python3
from __future__ import annotations

"""Instance identity helpers.

Goal: Avoid hardcoding agent/instance ids (e.g. 'etf_master') in scripts.

Priority:
1) AGENT_ID (set by gateway/hooks/refresh pipelines)
2) context.get_instance_id() (ETF_TW multi-tenant context)
3) fallback: 'etf_master' (legacy)
"""

import os


def get_instance_id_fallback(default: str = "etf_master") -> str:
    agent = os.environ.get("AGENT_ID") or os.environ.get("OPENCLAW_AGENT_NAME")
    if agent:
        return agent

    try:
        from scripts.etf_core import context

        cid = context.get_instance_id()
        if cid:
            return cid
    except Exception:
        pass

    return default
