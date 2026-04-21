"""
generate_learned_rules.py — EVOLUTION-01

每週六週報後執行。流程：
1. 讀 chain_breakdown + top_wins/losses → 組統計摘要 prompt
2. 注入 ai_decision_request.json wiki_context.learned_rules_draft
3. 呼叫 generate_ai_agent_response.py
4. 從 ai_decision_response.json 取 reasoning.learned_rules
5. 執行版本化滾動 → 寫 wiki/learned-rules.md + state/learned_rules_meta.json

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/generate_learned_rules.py [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core import context
from etf_core.state_io import safe_load_json, safe_load_jsonl, atomic_save_json

TW_TZ = ZoneInfo("Asia/Taipei")
MIN_SAMPLES = 5   # 樣本不足時跳過 LLM 呼叫
MAX_RULES = 15
STALE_WEEKS = 4


def _pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%"


def build_stats_prompt(
    chain_breakdown: dict,
    week_stats: dict,
    existing_rules: list[dict],
) -> str:
    """純函數：給定統計數據，回傳注入 AI Bridge 的 prompt 字串。"""
    rb = chain_breakdown or {}
    rule_b = rb.get("rule_engine", {})
    ai_b = rb.get("ai_bridge", {})
    tier1_b = rb.get("tier1_consensus", {})

    wins_txt = "\n".join(
        f"  - {w['symbol']} / {w['window']} / +{w['return_pct']}%"
        for w in (week_stats.get("top_wins") or [])
    ) or "  （無）"
    losses_txt = "\n".join(
        f"  - {l['symbol']} / {l['window']} / {l['return_pct']}%"
        for l in (week_stats.get("top_losses") or [])
    ) or "  （無）"

    existing_txt = "\n".join(
        f"{r['rule_id']}: {r['rule_text']}（出現{r['count']}次，{r['status']}）"
        for r in existing_rules
    ) or "  （尚無既有規則）"

    rule_loss_rate = _pct(rule_b.get('loss', 0) / rule_b['total'] if rule_b.get('total') else None)
    ai_loss_rate = _pct(ai_b.get('loss', 0) / ai_b['total'] if ai_b.get('total') else None)

    return f"""你是 ETF_Master 的決策品質分析師。
根據以下本週復盤統計，歸納出 1–5 條具體可執行的投資決策規則。

【本週統計】
- rule_engine: 總計 {rule_b.get('total', 0)} 筆, 勝率 {_pct(rule_b.get('win_rate'))}, 敗率 {rule_loss_rate}
- ai_bridge: 總計 {ai_b.get('total', 0)} 筆, 勝率 {_pct(ai_b.get('win_rate'))}, 敗率 {ai_loss_rate}
- tier1_consensus: 總計 {tier1_b.get('total', 0)} 筆, 勝率 {_pct(tier1_b.get('win_rate'))}
- 本週最準確:
{wins_txt}
- 本週最大失誤:
{losses_txt}

【現有規則庫摘要（避免重複）】
{existing_txt}

【輸出格式】（純 JSON array，無其他文字）
[
  {{
    "rule_text": "具體規則描述",
    "source_stats": "支撐此規則的統計數據摘要",
    "is_existing_rule_id": null
  }}
]
若要強化既有規則，將 is_existing_rule_id 填入對應 RULE-ID（如 "RULE-001"）。"""


def _week_diff(week_a: str, week_b: str) -> int:
    """回傳 week_b - week_a 的週數差（week_b 較新為正）。"""
    def _monday(wk: str) -> date:
        yr, wn = wk.split("-W")
        jan4 = date(int(yr), 1, 4)
        return jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=int(wn) - 1)
    return (_monday(week_b) - _monday(week_a)).days // 7


def _next_rule_id(existing_ids: list[str]) -> str:
    nums = []
    for rid in existing_ids:
        try:
            nums.append(int(rid.replace("RULE-", "")))
        except ValueError:
            pass
    return f"RULE-{(max(nums) + 1 if nums else 1):03d}"


def apply_rolling_logic(
    meta: dict,
    new_items: list[dict],
    current_week: str,
) -> dict:
    """
    純函數：給定現有 meta 和本週 LLM 新規則，回傳更新後的 meta。

    meta 結構：{"rules": [{"rule_id", "rule_text", "source_stats",
                            "count", "first_seen", "last_confirmed", "status"}, ...]}
    """
    rules: list[dict] = copy.deepcopy(meta.get("rules") or [])

    # 1. 標記 stale：超過 STALE_WEEKS 未出現
    for r in rules:
        if r.get("status") in ("tentative", "active"):
            diff = _week_diff(r["last_confirmed"], current_week)
            if diff > STALE_WEEKS:
                r["status"] = "stale"

    # 2. 處理本週新規則
    existing_ids = [r["rule_id"] for r in rules]
    for item in new_items:
        existing_id = item.get("is_existing_rule_id")
        if existing_id:
            # 強化既有規則
            for r in rules:
                if r["rule_id"] == existing_id:
                    r["count"] += 1
                    r["last_confirmed"] = current_week
                    r["source_stats"] = item.get("source_stats", r["source_stats"])
                    if r["count"] >= 2:
                        r["status"] = "active"
                    break
        else:
            # 全新規則
            new_id = _next_rule_id(existing_ids)
            existing_ids.append(new_id)
            rules.append({
                "rule_id": new_id,
                "rule_text": item["rule_text"],
                "source_stats": item.get("source_stats", ""),
                "count": 1,
                "first_seen": current_week,
                "last_confirmed": current_week,
                "status": "tentative",
            })

    # 3. 超過上限：淘汰最舊 stale（按 last_confirmed 升序）
    if len(rules) > MAX_RULES:
        stale = sorted(
            [r for r in rules if r["status"] == "stale"],
            key=lambda r: r["last_confirmed"],
        )
        to_remove = len(rules) - MAX_RULES
        remove_ids = {r["rule_id"] for r in stale[:to_remove]}
        rules = [r for r in rules if r["rule_id"] not in remove_ids]

    return {"rules": rules}


def parse_llm_output(raw: str) -> list[dict]:
    """解析 LLM 回傳的 JSON array。非法輸出回傳空 list。"""
    if not raw:
        return []
    text = raw.strip()
    # 去掉 markdown code fence
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        ).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    result = []
    for item in parsed:
        if isinstance(item, dict) and "rule_text" in item:
            result.append({
                "rule_text": str(item.get("rule_text", "")),
                "source_stats": str(item.get("source_stats", "")),
                "is_existing_rule_id": item.get("is_existing_rule_id"),
            })
    return result


def format_learned_rules_md(meta: dict, generated_at: str) -> str:
    """將 meta 轉成 wiki/learned-rules.md 格式（stale 規則不輸出）。"""
    active_rules = [r for r in (meta.get("rules") or []) if r.get("status") != "stale"]
    lines = [
        "## 學習規則庫",
        f"generated_at: {generated_at}",
        "",
    ]
    for r in active_rules:
        lines += [
            f"### {r['rule_id']}",
            f"- **規則**：{r['rule_text']}",
            f"- **來源統計**：{r['source_stats']}",
            f"- **出現次數**：{r['count']}",
            f"- **首次出現**：{r['first_seen']}",
            f"- **最後確認**：{r['last_confirmed']}",
            f"- **狀態**：{r['status']}",
            "",
        ]
    if not active_rules:
        lines.append("（本週尚無有效規則）")
    return "\n".join(lines) + "\n"


def _inject_learned_rules_draft_into_request(state_dir: Path, prompt: str) -> None:
    """將 learned_rules_draft 注入現有 ai_decision_request.json 的 wiki_context。"""
    req_path = state_dir / "ai_decision_request.json"
    payload = safe_load_json(req_path, {})
    wiki_ctx = payload.get("wiki_context") or {}
    wiki_ctx["learned_rules_draft"] = prompt
    payload["wiki_context"] = wiki_ctx
    atomic_save_json(req_path, payload)


def run(
    state_dir: Path | None = None,
    wiki_dir: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """
    執行完整的 learned-rules 更新流程。

    回傳:
        {"skipped": True, "reason": str}  — 跳過時
        {"skipped": False, "applied": bool, "rules_count": int, "would_write": str}
    """
    if state_dir is None:
        state_dir = context.get_state_dir()
    if wiki_dir is None:
        # profile-level wiki（generate_learned_rules.py 在 scripts/，parents[3] = profile root）
        wiki_dir = Path(__file__).resolve().parents[3] / "wiki"

    quality_report = safe_load_json(state_dir / "decision_quality_report.json", {})
    chain_breakdown = quality_report.get("chain_breakdown", {})

    # 樣本數檢查：以 rule_engine total 為基準
    rule_total = (chain_breakdown.get("rule_engine") or {}).get("total", 0)
    if rule_total < MIN_SAMPLES:
        print(f"[learned_rules] 跳過：rule_engine 樣本數 {rule_total} < {MIN_SAMPLES}")
        return {"skipped": True, "reason": "insufficient_samples"}

    # 讀本週統計
    today = datetime.now(tz=TW_TZ).date()
    iso_year, iso_week, _ = today.isocalendar()
    current_week = f"{iso_year}-W{iso_week:02d}"

    week_stats: dict = {
        "top_wins": quality_report.get("top_wins_latest") or [],
        "top_losses": quality_report.get("top_losses_latest") or [],
    }

    # 讀現有規則庫 meta
    meta = safe_load_json(state_dir / "learned_rules_meta.json", {"rules": []})
    existing_rules = meta.get("rules", [])

    # 組 prompt 注入 request
    prompt = build_stats_prompt(chain_breakdown, week_stats, existing_rules)
    _inject_learned_rules_draft_into_request(state_dir, prompt)

    # 讀 ai_decision_response（由呼叫方先執行 generate_ai_agent_response.py）
    response = safe_load_json(state_dir / "ai_decision_response.json", {})
    raw_learned = (response.get("reasoning") or {}).get("learned_rules", "")

    if not raw_learned:
        print("[learned_rules] ai_decision_response.reasoning.learned_rules 為空，跳過本週更新")
        return {"skipped": False, "applied": False, "rules_count": len(existing_rules), "reason": "no_llm_output"}

    new_items = parse_llm_output(raw_learned)
    if not new_items:
        print("[learned_rules] LLM 輸出解析失敗，跳過")
        return {"skipped": False, "applied": False, "rules_count": len(existing_rules), "reason": "parse_failed"}

    updated_meta = apply_rolling_logic(meta, new_items, current_week)
    now_str = datetime.now(tz=TW_TZ).isoformat()
    md_content = format_learned_rules_md(updated_meta, generated_at=now_str)

    if dry_run:
        return {"skipped": False, "applied": False, "would_write": md_content,
                "rules_count": len(updated_meta["rules"])}

    # 寫 wiki + meta
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "learned-rules.md").write_text(md_content, encoding="utf-8")
    updated_meta["last_updated"] = now_str
    atomic_save_json(state_dir / "learned_rules_meta.json", updated_meta)

    active = sum(1 for r in updated_meta["rules"] if r["status"] != "stale")
    print(f"[learned_rules] 完成 — {active} 條有效規則寫入 wiki/learned-rules.md")
    return {"skipped": False, "applied": True, "rules_count": len(updated_meta["rules"])}


def main() -> None:
    parser = argparse.ArgumentParser(description="產出 wiki/learned-rules.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
