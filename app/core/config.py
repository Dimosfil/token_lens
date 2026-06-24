from __future__ import annotations

import json
import os
import glob
from pathlib import Path

from app.core.codex_discovery import discover_codex_paths, discover_opencode_paths


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.json"
LOCAL_CONFIG_PATH = ROOT / "config.local.json"
PATH_KEYS = (
    "analytics_db",
    "codex_logs_db",
    "codex_session_index",
    "opencode_db",
    "opencode_tokens_jsonl",
    "log_file",
    "logging_file",
)
REQUIRED_CODEX_KEYS = ("codex_logs_db",)
DISCOVERED_SOURCE_KEYS = (
    "codex_logs_db",
    "codex_session_index",
    "opencode_db",
    "opencode_tokens_jsonl",
)


def load_config() -> dict:
    config = _read_json(CONFIG_PATH)
    local_config = {}
    if LOCAL_CONFIG_PATH.exists():
        local_config = _read_json(LOCAL_CONFIG_PATH)
        config.update(local_config)

    discovered: dict[str, str] = {}
    if config.get("auto_discover_codex_sources", True):
        discovered.update(discover_codex_paths())
    if config.get("auto_discover_opencode_sources", True):
        discovered.update(discover_opencode_paths())

    local_updates: dict[str, str] = {}
    for key, value in discovered.items():
        if _should_use_discovered_path(key, config):
            config[key] = value
            local_updates[key] = value

    if local_updates:
        _write_local_source_updates(local_config, local_updates)

    for key in PATH_KEYS:
        if config.get(key):
            config[key] = str(_resolve_config_path(config[key]))

    return config


def validate_codex_source_config(config: dict) -> list[str]:
    """Return human-readable Codex source configuration blockers."""
    issues: list[str] = []
    for key in REQUIRED_CODEX_KEYS:
        if not str(config.get(key) or "").strip():
            issues.append(f"{key} is not configured")

    logs_db = str(config.get("codex_logs_db") or "").strip()
    if logs_db:
        issues.extend(_validate_readable_file("codex_logs_db", logs_db))

    session_index = str(config.get("codex_session_index") or "").strip()
    if session_index:
        issues.extend(_validate_readable_path_set("codex_session_index", session_index))

    return issues


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_local_source_updates(local_config: dict, updates: dict[str, str]) -> None:
    local_config = dict(local_config)
    for key, value in updates.items():
        if key in DISCOVERED_SOURCE_KEYS:
            local_config[key] = value
    LOCAL_CONFIG_PATH.write_text(
        json.dumps(local_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _should_use_discovered_path(key: str, config: dict) -> bool:
    value = str(config.get(key) or "").strip()
    if not value:
        return True
    return not _configured_path_exists(value)


def _resolve_config_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def _validate_readable_file(key: str, value: str) -> list[str]:
    path = Path(value)
    if not path.exists():
        return [f"{key} does not exist: {path}"]
    if not path.is_file():
        return [f"{key} is not a file: {path}"]
    if not os.access(path, os.R_OK):
        return [f"{key} is not readable: {path}"]
    return []


def _configured_path_exists(value: str) -> bool:
    if _has_glob(value):
        return any(Path(item).is_file() for item in glob.glob(value, recursive=True))
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.exists()


def _validate_readable_path_set(key: str, value: str) -> list[str]:
    if _has_glob(value):
        matches = [Path(item) for item in glob.glob(value, recursive=True)]
        files = [path for path in matches if path.is_file()]
        if not files:
            return [f"{key} glob does not match any files: {value}"]
        unreadable = [path for path in files if not os.access(path, os.R_OK)]
        if unreadable:
            return [f"{key} has unreadable files: {unreadable[0]}"]
        return []

    path = Path(value)
    if path.is_dir():
        if not os.access(path, os.R_OK):
            return [f"{key} directory is not readable: {path}"]
        return []
    return _validate_readable_file(key, value)


def _has_glob(value: str) -> bool:
    return any(char in value for char in ("*", "?", "["))
