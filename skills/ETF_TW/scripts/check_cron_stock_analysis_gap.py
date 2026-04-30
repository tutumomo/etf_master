#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


MISSING_PATTERNS = (
    "stock-analysis-tw 腳本不存在",
    "stock-analysis-tw analyze_stock.py 缺失",
    "stock-analysis-tw/analyze_stock.py 目前未安裝/不存在",
    "找不到 `skills/stock-analysis-tw/scripts/analyze_stock.py`",
)
LIVE_SCRIPT_PATTERN = "skills/stock-analysis-tw/scripts/analyze_stock.py"


def _parse_output_timestamp(path: Path) -> datetime | None:
    try:
        return datetime.strptime(path.stem, "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        return None


def _load_jobs(path: Path) -> dict:
    if not path.exists():
        return {"jobs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def find_live_prompt_dependencies(jobs_payload: dict) -> list[str]:
    offenders = []
    for job in jobs_payload.get("jobs", []):
        prompt = job.get("prompt") or ""
        if LIVE_SCRIPT_PATTERN in prompt:
            offenders.append(job.get("name") or job.get("id") or "unknown")
    return offenders


def find_recent_missing_script_reports(output_dir: Path, *, since: datetime | None = None) -> list[dict]:
    reports: list[dict] = []
    if not output_dir.exists():
        return reports
    for path in sorted(output_dir.glob("*.md")):
        ts = _parse_output_timestamp(path)
        if since and (ts is None or ts < since):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        matched = [p for p in MISSING_PATTERNS if p in text]
        if matched:
            reports.append({
                "file": str(path),
                "run_at": ts.isoformat() if ts else None,
                "patterns": matched,
            })
    return reports


def build_gap_report(root: Path, *, job_id: str = "1090aafd4264", since: datetime | None = None) -> dict:
    jobs_payload = _load_jobs(root / "cron" / "jobs.json")
    prompt_offenders = find_live_prompt_dependencies(jobs_payload)
    output_reports = find_recent_missing_script_reports(root / "cron" / "output" / job_id, since=since)
    return {
        "ok": not prompt_offenders and not output_reports,
        "job_id": job_id,
        "since": since.isoformat() if since else None,
        "live_prompt_offenders": prompt_offenders,
        "recent_missing_script_reports": output_reports,
        "recent_missing_script_count": len(output_reports),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--job-id", default="1090aafd4264")
    parser.add_argument("--since", help="Only scan cron output at or after YYYY-MM-DDTHH:MM:SS")
    args = parser.parse_args()

    since = datetime.fromisoformat(args.since) if args.since else None
    report = build_gap_report(args.root, job_id=args.job_id, since=since)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
