#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def build_layered_review_status(state_dir: Path, request_id: str | None = None) -> dict:
    base = state_dir / "layered_review_reviews"
    if not base.exists():
        return {
            "ok": True,
            "updated_at": datetime.now().astimezone().isoformat(),
            "request_id": request_id,
            "windows": {},
            "note": "no layered_review_reviews directory",
        }

    # If request_id not specified, pick the most recently updated request directory.
    if not request_id:
        candidates = [p for p in base.iterdir() if p.is_dir()]
        candidates.sort(key=lambda p: (p.stat().st_mtime if p.exists() else 0), reverse=True)
        if candidates:
            request_id = candidates[0].name

    if not request_id:
        return {
            "ok": True,
            "updated_at": datetime.now().astimezone().isoformat(),
            "request_id": None,
            "windows": {},
            "note": "no request directories",
        }

    req_dir = base / request_id
    index_path = req_dir / "index.json"
    index = _load_json(index_path)

    # Fallback: derive windows from files
    windows = index.get("windows") if isinstance(index.get("windows"), dict) else {}
    if not windows:
        for p in req_dir.glob("*.json"):
            if p.name == "index.json":
                continue
            win = p.stem
            artifact = _load_json(p)
            outcome = artifact.get("outcome") if isinstance(artifact.get("outcome"), dict) else {}
            windows[win] = {
                "path": str(p),
                "updated_at": artifact.get("updated_at"),
                "review_window_label": artifact.get("review_window_label"),
                "outcome_status": outcome.get("outcome_status") or outcome.get("status"),
                "outcome_note": outcome.get("outcome_note") or outcome.get("note"),
            }

    return {
        "ok": True,
        "updated_at": datetime.now().astimezone().isoformat(),
        "request_id": request_id,
        "index_path": str(index_path),
        "windows": windows,
        "source": "layered_review_reviews",
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: read_layered_review_artifacts.py <state_dir> [request_id]", file=sys.stderr)
        return 2
    state_dir = Path(sys.argv[1])
    request_id = sys.argv[2] if len(sys.argv) > 2 else None
    payload = build_layered_review_status(state_dir, request_id=request_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
