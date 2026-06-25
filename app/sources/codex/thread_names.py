from __future__ import annotations

import glob
import json
import re
from pathlib import Path


MAX_DERIVED_THREAD_NAME_LENGTH = 96


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
        paths = [index_path]
        sibling_sessions = index_path.parent / "sessions"
        if index_path.name == "session_index.jsonl" and sibling_sessions.is_dir():
            paths.extend(sorted(sibling_sessions.rglob("*.jsonl")))
        return paths
    return []


def _has_glob(value: str) -> bool:
    return any(char in value for char in ("*", "?", "["))


def _load_thread_names_file(index_path: Path, names: dict[str, str]) -> None:
    if not index_path.exists() or not index_path.is_file():
        return

    file_thread_id: str | None = None
    derived_thread_name: str | None = None
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            thread_id = _first_text(row, ("id", "thread_id", "session_id", "conversation_id"))
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if not thread_id:
                thread_id = _first_text(payload, ("id", "thread_id", "session_id", "conversation_id"))

            thread_name = _first_text(row, ("thread_name", "title", "name", "conversation_title"))
            if not thread_name:
                thread_name = _first_text(payload, ("thread_name", "title", "name", "conversation_title"))
            if thread_id and thread_name:
                names[thread_id] = thread_name
            if not file_thread_id:
                file_thread_id = thread_id
            if not derived_thread_name:
                derived_thread_name = _user_message_title(row)

    if file_thread_id and derived_thread_name and file_thread_id not in names:
        names[file_thread_id] = derived_thread_name


def _first_text(row: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _user_message_title(row: dict) -> str | None:
    if row.get("type") != "response_item":
        return None
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if payload.get("role") != "user":
        return None
    text = _content_text(payload.get("content"))
    if _is_bootstrap_user_message(text):
        return None
    return _clean_title(_extract_codex_request(text))


def _content_text(content) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts)
    return None


def _clean_title(value: str | None) -> str | None:
    text = re.sub(r"\s+", " ", value or "").strip()
    if not text:
        return None
    if len(text) <= MAX_DERIVED_THREAD_NAME_LENGTH:
        return text
    return text[: MAX_DERIVED_THREAD_NAME_LENGTH - 3].rstrip() + "..."


def _is_bootstrap_user_message(value: str | None) -> bool:
    text = (value or "").lstrip()
    return (
        text.startswith("# AGENTS.md instructions")
        or text.startswith("<environment_context>")
        or "<INSTRUCTIONS>" in text[:500]
    )


def _extract_codex_request(value: str | None) -> str | None:
    text = value or ""
    marker = "My request for Codex:"
    if marker in text:
        text = text.split(marker, 1)[1]
    text = re.sub(r"<image\b.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text
