from __future__ import annotations

import json
from pathlib import Path


def load_thread_names(path: str) -> dict[str, str]:
    index_path = Path(path)
    if not index_path.exists():
        return {}

    names: dict[str, str] = {}
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            thread_id = row.get("id")
            thread_name = row.get("thread_name")
            if thread_id and thread_name:
                names[thread_id] = thread_name
    return names
