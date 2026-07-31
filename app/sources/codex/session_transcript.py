from __future__ import annotations

import glob
import json
import re
from pathlib import Path


SAFE_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{12,128}$")


def load_turn_payloads(
    configured_path: str,
    thread_id: str,
    turn_ids: set[str],
) -> dict[str, dict]:
    """Read selected turn messages from the matching Codex transcript only."""
    safe_turn_ids = {value for value in turn_ids if isinstance(value, str) and value}
    if not SAFE_THREAD_ID_RE.fullmatch(str(thread_id or "")) or not safe_turn_ids:
        return {}

    session_path = _matching_session_path(configured_path, thread_id)
    if session_path is None:
        return {}
    return _read_session_file(session_path, thread_id, safe_turn_ids)


def _matching_session_path(configured_path: str, thread_id: str) -> Path | None:
    candidates = _session_candidates(configured_path, thread_id)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (_safe_mtime(path), str(path)))


def _session_candidates(configured_path: str, thread_id: str) -> list[Path]:
    text = str(configured_path or "").strip()
    if not text:
        return []

    if _has_glob(text):
        paths = [Path(item) for item in glob.glob(text, recursive=True)]
        return _matching_files(paths, thread_id)

    configured = Path(text)
    if configured.is_dir():
        return _safe_directory_matches(configured, thread_id)
    if configured.is_file():
        if thread_id in configured.name and configured.suffix.lower() == ".jsonl":
            return [configured]
        if configured.name == "session_index.jsonl":
            sessions = configured.parent / "sessions"
            if sessions.is_dir():
                return _safe_directory_matches(sessions, thread_id)
    return []


def _safe_directory_matches(root: Path, thread_id: str) -> list[Path]:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return []

    matches: list[Path] = []
    for candidate in root.rglob(f"*{thread_id}*.jsonl"):
        try:
            resolved_candidate = candidate.resolve(strict=True)
            resolved_candidate.relative_to(resolved_root)
        except (OSError, ValueError):
            continue
        if resolved_candidate.is_file():
            matches.append(resolved_candidate)
    return matches


def _matching_files(paths: list[Path], thread_id: str) -> list[Path]:
    matches = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".jsonl" and thread_id in path.name:
            matches.append(path)
    return matches


def _read_session_file(path: Path, thread_id: str, turn_ids: set[str]) -> dict[str, dict]:
    collected = {
        turn_id: {"request_messages": [], "response_messages": []}
        for turn_id in turn_ids
    }
    current_turn_id: str | None = None
    verified_thread = False

    try:
        with path.open("r", encoding="utf-8") as transcript:
            for line in transcript:
                row = _decode_row(line)
                if row is None:
                    continue
                payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
                row_type = row.get("type")
                payload_type = payload.get("type")

                if row_type == "session_meta" and _session_thread_id(payload) == thread_id:
                    verified_thread = True

                if row_type == "event_msg" and payload_type == "task_started":
                    candidate_turn_id = payload.get("turn_id")
                    current_turn_id = candidate_turn_id if candidate_turn_id in turn_ids else None
                    continue

                if row_type == "event_msg" and payload_type == "task_complete":
                    if payload.get("turn_id") == current_turn_id:
                        current_turn_id = None
                    continue

                if current_turn_id is None:
                    continue
                if row_type == "event_msg" and payload_type == "user_message":
                    message = _user_message(row, payload)
                    if message is not None:
                        collected[current_turn_id]["request_messages"].append(message)
                elif (
                    row_type == "response_item"
                    and payload_type == "message"
                    and payload.get("role") == "assistant"
                ):
                    message = _assistant_message(row, payload)
                    if message is not None:
                        collected[current_turn_id]["response_messages"].append(message)
    except (OSError, UnicodeError):
        return {}

    if not verified_thread:
        return {}
    return {
        turn_id: _build_turn_payload(turn_id, messages)
        for turn_id, messages in collected.items()
        if messages["request_messages"] or messages["response_messages"]
    }


def _decode_row(line: str) -> dict | None:
    try:
        row = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    return row if isinstance(row, dict) else None


def _session_thread_id(payload: dict) -> str | None:
    for key in ("id", "thread_id", "session_id", "conversation_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _user_message(row: dict, payload: dict) -> dict | None:
    text = payload.get("message")
    if not isinstance(text, str) or not text.strip():
        return None
    message = {"timestamp": row.get("timestamp"), "text": text}
    images = payload.get("images")
    local_images = payload.get("local_images")
    if isinstance(images, list) and images:
        message["images"] = images
    if isinstance(local_images, list) and local_images:
        message["local_images"] = local_images
    return message


def _assistant_message(row: dict, payload: dict) -> dict | None:
    text = _content_text(payload.get("content"))
    if not text:
        return None
    message = {"timestamp": row.get("timestamp"), "text": text}
    phase = payload.get("phase")
    if isinstance(phase, str) and phase:
        message["phase"] = phase
    return message


def _content_text(content) -> str | None:
    if isinstance(content, str):
        return content.strip() or None
    if not isinstance(content, list):
        return None
    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                parts.append(text)
    combined = "\n".join(part for part in parts if part).strip()
    return combined or None


def _build_turn_payload(turn_id: str, messages: dict) -> dict:
    result = {}
    if messages["request_messages"]:
        result["request"] = {
            "source": "codex_session_transcript",
            "turn_id": turn_id,
            "messages": messages["request_messages"],
        }
    if messages["response_messages"]:
        result["response"] = {
            "source": "codex_session_transcript",
            "turn_id": turn_id,
            "messages": messages["response_messages"],
        }
    return result


def _has_glob(value: str) -> bool:
    return any(char in value for char in ("*", "?", "["))


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0
