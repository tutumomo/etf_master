#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def safe_load_json(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        text = path.read_text(encoding='utf-8').strip()
        if not text:
            return default
        return json.loads(text)
    except Exception:
        return default


def atomic_save_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=str(path.parent), delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
    return path


def safe_append_jsonl(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return path


def safe_load_jsonl(path: Path) -> list[Any]:
    if not path.exists():
        return []
    rows = []
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    except Exception:
        return []
    return rows
