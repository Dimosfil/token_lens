from __future__ import annotations

import glob
import json
from pathlib import Path


def load_thread_names(path: str) -> dict[str, str]:
    names: dict[str, str] = {}
    for index_path in _session_index_paths(path):
        _load_thread_names_file(index_path, names)
    return names


def _session_index_paths(path: str) -> list[Path]:
    text = str(path or "").strip()
    if not text:
        return []

    if _has_glob(text):
        return sorted(Path(item) for item in glob.glob(text, recursive=True) if Path(item).is_file())

    index_path = Path(text)
    if index_path.is_dir():
        return sorted(index_path.rglob("*.jsonl"))
    if index_path.is_file():
        return [index_path]
    return []


def _has_glob(value: str) -> bool:
    return any(char in value for char in ("*", "?", "["))


def _load_thread_names_file(index_path: Path, names: dict[str, str]) -> None:
    if not index_path.exists() or not index_path.is_file():
        return

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
