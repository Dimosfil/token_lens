from __future__ import annotations

import json
import os
from pathlib import Path


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


def load_config() -> dict:
    config = _read_json(CONFIG_PATH)
    if LOCAL_CONFIG_PATH.exists():
        config.update(_read_json(LOCAL_CONFIG_PATH))

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
        issues.extend(_validate_readable_file("codex_session_index", session_index))

    return issues


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
