#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from layered_review_schedule_plan import build_layered_review_schedule_plan


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def write_layered_review_plan(state_dir: Path, request_id: str) -> dict:
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = build_layered_review_schedule_plan(request_id=request_id)
    (state_dir / 'layered_review_plan.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding='utf-8',
    )
    _append_jsonl(state_dir / 'layered_review_plan.jsonl', payload)
    return payload


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('state_dir', nargs='?', default=str(ROOT / 'instances' / 'etf_master' / 'state'))
    parser.add_argument('request_id', nargs='?', default='missing-request-id')
    args = parser.parse_args()

    target_dir = Path(args.state_dir)
    request_id = args.request_id

    print(json.dumps(write_layered_review_plan(target_dir, request_id), ensure_ascii=False, indent=2))
