from __future__ import annotations

import glob
import json
import re
import sqlite3
from pathlib import Path


MAX_DERIVED_THREAD_NAME_LENGTH = 96


def load_thread_names(path: str) -> dict[str, str]:
    names: dict[str, str] = {}
    index_paths = _session_index_paths(path)
    for index_path in index_paths:
        _load_thread_names_file(index_path, names)
    for state_path in _state_db_candidates(path, index_paths):
        _load_state_thread_titles(state_path, names)
    return names


def load_thread_metadata(path: str) -> dict[str, dict]:
    metadata: dict[str, dict] = {}
    index_paths = _session_index_paths(path)
    for state_path in _state_db_candidates(path, index_paths):
        _load_state_thread_metadata(state_path, metadata)
    return metadata


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


def _state_db_candidates(path: str, session_paths: list[Path]) -> list[Path]:
    candidates: list[Path] = []
    text = str(path or "").strip()
    if text and not _has_glob(text):
        index_path = Path(text)
        roots = [index_path if index_path.is_dir() else index_path.parent]
        roots.extend(parent for parent in roots[0].parents if parent.name == ".codex")
        for root in roots:
            candidates.append(root / "state_5.sqlite")

    for session_path in session_paths:
        for parent in session_path.parents:
            if parent.name == ".codex":
                candidates.append(parent / "state_5.sqlite")
                break

    seen = set()
    unique = []
    for candidate in candidates:
        resolved = str(candidate)
        if resolved in seen:
            continue
        seen.add(resolved)
        if candidate.is_file():
            unique.append(candidate)
    return unique


def _load_state_thread_titles(state_path: Path, names: dict[str, str]) -> None:
    try:
        con = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return
    try:
        rows = con.execute(
            """
            select id, title
            from threads
            where title is not null and trim(title) != ''
            """
        ).fetchall()
    except sqlite3.Error:
        return
    finally:
        con.close()

    for thread_id, title in rows:
        if isinstance(thread_id, str) and isinstance(title, str) and title.strip():
            names[thread_id] = title.strip()


def _load_state_thread_metadata(state_path: Path, metadata: dict[str, dict]) -> None:
    try:
        con = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return
    try:
        rows = con.execute(
            """
            select id, title, preview, tokens_used, model, reasoning_effort, cwd, updated_at, recency_at
            from threads
            where id is not null and trim(id) != ''
            """
        ).fetchall()
    except sqlite3.Error:
        return
    finally:
        con.close()

    for row in rows:
        thread_id = row[0]
        if not isinstance(thread_id, str) or not thread_id.strip():
            continue
        metadata[thread_id] = {
            "thread_id": thread_id,
            "thread_name": _text_or_none(row[1]),
            "preview": _text_or_none(row[2]),
            "tokens_used": _int_or_zero(row[3]),
            "model": _text_or_none(row[4]),
            "reasoning_effort": _text_or_none(row[5]),
            "cwd": _text_or_none(row[6]),
            "updated_at": _int_or_none(row[7]),
            "recency_at": _int_or_none(row[8]),
        }


def _text_or_none(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _int_or_zero(value) -> int:
    parsed = _int_or_none(value)
    return parsed if parsed is not None else 0


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
