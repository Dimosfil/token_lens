from __future__ import annotations

import os
import shutil
from pathlib import Path


def discover_codex_paths(env: dict[str, str] | None = None) -> dict[str, str]:
    env = env or os.environ
    roots = _candidate_roots(env)
    discovered: dict[str, str] = {}

    logs_db = _first_existing_file([
        root / "sqlite" / "logs_2.sqlite"
        for root in roots
    ] + [
        root / "logs_2.sqlite"
        for root in roots
    ])
    if logs_db:
        discovered["codex_logs_db"] = str(logs_db)

    session_index = _first_existing_path([
        root / "sessions"
        for root in roots
    ] + [
        root / "session_index.jsonl"
        for root in roots
    ])
    if session_index:
        discovered["codex_session_index"] = str(session_index)

    return discovered


def discover_opencode_paths(env: dict[str, str] | None = None) -> dict[str, str]:
    env = env or os.environ
    discovered: dict[str, str] = {}

    db_path = _first_existing_file(_opencode_db_candidates(env))
    if db_path:
        discovered["opencode_db"] = str(db_path)

    tokens_path = _first_existing_file(_opencode_tokens_candidates(env))
    if tokens_path:
        discovered["opencode_tokens_jsonl"] = str(tokens_path)

    return discovered


def discover_codex_command(env: dict[str, str] | None = None) -> str | None:
    env = env or os.environ
    roots = _candidate_roots(env)
    command = _first_existing_file(
        [root / "bin" / name for root in roots for name in _codex_command_names()]
        + _user_bin_commands(env)
    )
    if command:
        return str(command)
    return shutil.which("codex.cmd") or shutil.which("codex.exe") or shutil.which("codex")


def _candidate_roots(env: dict[str, str]) -> list[Path]:
    roots: list[Path] = []
    for key in ("CODEX_HOME", "CODEX_CONFIG_HOME"):
        value = str(env.get(key) or "").strip()
        if value:
            roots.append(Path(value).expanduser())

    user_profile = str(env.get("USERPROFILE") or "").strip()
    if user_profile:
        roots.append(Path(user_profile) / ".codex")

    home_drive = str(env.get("HOMEDRIVE") or "").strip()
    home_path = str(env.get("HOMEPATH") or "").strip()
    if home_drive and home_path:
        roots.append(Path(home_drive + home_path) / ".codex")

    home = str(env.get("HOME") or "").strip()
    if home:
        roots.append(Path(home) / ".codex")

    return _dedupe_paths(roots)


def _codex_command_names() -> list[str]:
    return ["codex.cmd", "codex.exe", "codex"]


def _user_bin_commands(env: dict[str, str]) -> list[Path]:
    paths: list[Path] = []
    user_profile = str(env.get("USERPROFILE") or "").strip()
    app_data = str(env.get("APPDATA") or "").strip()
    if app_data:
        paths.extend(Path(app_data) / "npm" / name for name in _codex_command_names())
    elif user_profile:
        paths.extend(Path(user_profile) / "AppData" / "Roaming" / "npm" / name for name in _codex_command_names())
    if user_profile:
        paths.extend(Path(user_profile) / ".codex" / "bin" / name for name in _codex_command_names())
    return paths


def _opencode_db_candidates(env: dict[str, str]) -> list[Path]:
    paths: list[Path] = []
    xdg_data_home = str(env.get("XDG_DATA_HOME") or "").strip()
    if xdg_data_home:
        paths.append(Path(xdg_data_home).expanduser() / "opencode" / "opencode.db")

    local_app_data = str(env.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        paths.append(Path(local_app_data) / "opencode" / "opencode.db")

    for home in _home_roots(env):
        paths.extend([
            home / ".local" / "share" / "opencode" / "opencode.db",
            home / "AppData" / "Local" / "opencode" / "opencode.db",
        ])
    return _dedupe_paths(paths)


def _opencode_tokens_candidates(env: dict[str, str]) -> list[Path]:
    paths: list[Path] = []
    xdg_config_home = str(env.get("XDG_CONFIG_HOME") or "").strip()
    if xdg_config_home:
        paths.append(Path(xdg_config_home).expanduser() / "opencode" / "logs" / "token-tracker" / "tokens.jsonl")

    app_data = str(env.get("APPDATA") or "").strip()
    if app_data:
        paths.append(Path(app_data) / "opencode" / "logs" / "token-tracker" / "tokens.jsonl")

    for home in _home_roots(env):
        paths.extend([
            home / ".config" / "opencode" / "logs" / "token-tracker" / "tokens.jsonl",
            home / "AppData" / "Roaming" / "opencode" / "logs" / "token-tracker" / "tokens.jsonl",
        ])
    return _dedupe_paths(paths)


def _home_roots(env: dict[str, str]) -> list[Path]:
    roots: list[Path] = []
    user_profile = str(env.get("USERPROFILE") or "").strip()
    if user_profile:
        roots.append(Path(user_profile))

    home_drive = str(env.get("HOMEDRIVE") or "").strip()
    home_path = str(env.get("HOMEPATH") or "").strip()
    if home_drive and home_path:
        roots.append(Path(home_drive + home_path))

    home = str(env.get("HOME") or "").strip()
    if home:
        roots.append(Path(home).expanduser())

    return _dedupe_paths(roots)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _first_existing_file(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def _first_existing_path(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file() or path.is_dir():
            return path
    return None
