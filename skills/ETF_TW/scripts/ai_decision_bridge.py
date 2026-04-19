#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

TW_TZ = ZoneInfo('Asia/Taipei')


def _now_iso() -> str:
    return datetime.now(TW_TZ).isoformat()


def build_ai_decision_request(
    *,
    requested_by: str,
    mode: str,
    context_version: str,
    inputs: dict,
) -> dict:
    now = _now_iso()
    return {
        "request_id": f"ai-decision-request-{uuid4().hex[:12]}",
        "created_at": now,
        "requested_by": requested_by,
        "mode": mode,
        "context_version": context_version,
        "context_updated_at": now,
        "inputs": inputs or {},
    }


def build_ai_decision_request_from_state(
    *,
    strategy: dict,
    positions: dict,
    orders_open: dict,
    fills_ledger: dict,
    portfolio_snapshot: dict,
    market_cache: dict,
    market_intelligence: dict,
    intraday_tape_context: dict,
    market_context_taiwan: dict,
    market_event_context: dict,
    market_calendar_status: dict,
    reconciliation: dict,
    decision_memory_context: dict | None = None,
    worldmonitor_snapshot: dict | None = None,
    worldmonitor_alerts: list[dict] | None = None,
    requested_by: str,
    mode: str,
    context_version: str,
) -> dict:
    inputs = {
        "strategy": strategy or {},
        "positions": positions or {},
        "orders_open": orders_open or {},
        "fills_ledger": fills_ledger or {},
        "portfolio_snapshot": portfolio_snapshot or {},
        "market_cache": market_cache or {},
        "market_intelligence": market_intelligence or {},
        "intraday_tape_context": intraday_tape_context or {},
        "market_context_taiwan": market_context_taiwan or {},
        "market_event_context": market_event_context or {},
        "market_calendar_status": market_calendar_status or {},
        "reconciliation": reconciliation or {},
        "decision_memory_context": decision_memory_context or {},
        "worldmonitor_context": _build_worldmonitor_context(
            worldmonitor_snapshot or {}, worldmonitor_alerts or []
        ),
    }
    return build_ai_decision_request(
        requested_by=requested_by,
        mode=mode,
        context_version=context_version,
        inputs=inputs,
    )


def build_ai_decision_response(
    *,
    request_id: str,
    summary: str,
    action: str,
    confidence: str,
    uncertainty: str | None = None,
    strategy_alignment: str | None = None,
    candidate: dict | None = None,
    warnings: list[str] | None = None,
    input_refs: dict | None = None,
    consensus: dict | None = None,
    expires_in_minutes: int = 30,
) -> dict:
    now = datetime.now(TW_TZ)
    expires_at = (now + timedelta(minutes=expires_in_minutes)).isoformat()
    return {
        "request_id": request_id,
        "generated_at": now.isoformat(),
        "expires_at": expires_at,
        "stale": False,
        "source": "ai_decision_bridge",
        "agent": {
            "name": "ETF_Master",
            "version": "phase1-minimum",
        },
        "decision": {
            "summary": summary,
            "action": action,
            "confidence": confidence,
            "uncertainty": uncertainty or "unknown",
            "strategy_alignment": strategy_alignment or "unknown",
        },
        "candidate": candidate or {},
        "reasoning": {
            "market_context_summary": "",
            "position_context_summary": "",
            "risk_context_summary": "",
        },
        "warnings": warnings or [],
        "input_refs": input_refs or {},
        "consensus": consensus,
    }


def default_ai_decision_request_payload() -> dict:
    return {
        "request_id": "bootstrap-ai-decision-request",
        "created_at": None,
        "requested_by": "system",
        "mode": "decision_only",
        "context_version": "bootstrap",
        "context_updated_at": None,
        "inputs": {},
    }


def default_ai_decision_response_payload() -> dict:
    return {
        "request_id": "bootstrap-ai-decision-request",
        "generated_at": None,
        "expires_at": None,
        "stale": True,
        "source": "ai_decision_bridge",
        "agent": {
            "name": "ETF_Master",
            "version": "phase1-minimum",
        },
        "decision": {
            "summary": "尚無 AI 建議",
            "action": "hold",
            "confidence": "unknown",
            "uncertainty": "unknown",
            "strategy_alignment": "unknown",
        },
        "candidate": {},
        "reasoning": {
            "market_context_summary": "",
            "position_context_summary": "",
            "risk_context_summary": "",
        },
        "warnings": [],
        "input_refs": {},
        "consensus": None,
    }


def is_ai_decision_response_stale(payload: dict) -> bool:
    expires_at = payload.get("expires_at")
    if not expires_at:
        return True
    try:
        return datetime.fromisoformat(expires_at) <= datetime.now(TW_TZ)
    except Exception:
        return True


def build_agent_consumed_response_payload(
    *,
    request_id: str,
    summary: str,
    action: str,
    confidence: str,
    agent_name: str,
    review_status: str,
    reasoning: dict | None = None,
    input_refs: dict | None = None,
    candidate: dict | None = None,
    warnings: list[str] | None = None,
    uncertainty: str | None = None,
    strategy_alignment: str | None = None,
    consensus: dict | None = None,
    expires_in_minutes: int = 30,
) -> dict:
    payload = build_ai_decision_response(
        request_id=request_id,
        summary=summary,
        action=action,
        confidence=confidence,
        uncertainty=uncertainty,
        strategy_alignment=strategy_alignment,
        candidate=candidate,
        warnings=warnings,
        input_refs=input_refs,
        consensus=consensus,
        expires_in_minutes=expires_in_minutes,
    )
    payload["source"] = "ai_agent"
    payload["agent"] = {
        "name": agent_name,
        "version": "agent-consumed-phase0",
    }
    if reasoning:
        payload["reasoning"] = {
            **payload.get("reasoning", {}),
            **reasoning,
        }
    payload["review"] = {
        "status": review_status,
        "reviewed_at": None,
        "human_feedback": None,
    }
    return payload


def _build_worldmonitor_context(snapshot: dict, alerts: list[dict]) -> dict:
    """將 worldmonitor snapshot + alerts 整理成 AI 決策橋的第 13 個輸入源"""
    level_rank = {'L1': 1, 'L2': 2, 'L3': 3}
    highest = 'none'
    affected_signals: dict[str, dict] = {}

    for alert in alerts:
        sev = alert.get('severity', 'L1')
        if level_rank.get(sev, 0) > level_rank.get(highest, 0):
            highest = sev
        for etf in alert.get('affected_etfs', []):
            if etf not in affected_signals:
                affected_signals[etf] = {}
            affected_signals[etf][alert.get('alert_type', 'unknown')] = alert.get('title', '')

    sc = snapshot.get('supply_chain', {})
    geo = snapshot.get('geopolitical', {})

    return {
        'supply_chain_stress': sc.get('global_stress_level', 'unknown'),
        'geopolitical_risk': geo.get('global_risk_level', 'unknown'),
        'taiwan_strait_risk': geo.get('taiwan_strait_risk', 'unknown'),
        'active_alerts_count': len(alerts),
        'highest_alert_severity': highest,
        'affected_etf_signals': affected_signals,
    }
