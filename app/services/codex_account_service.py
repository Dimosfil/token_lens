from __future__ import annotations

import atexit
import os
import threading
import time

from app.core.codex_discovery import discover_codex_command, is_usable_codex_command
from app.services.codex_app_server_client import CodexAppServerClient
from app.services.codex_app_server_client import request_rate_limits_once as _request_rate_limits_once
from app.services.codex_rate_limits import normalize_rate_limits as _normalize_rate_limits
from app.services.codex_rate_limits import safe_int as _safe_int


DEFAULT_CACHE_SECONDS = 3
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_IDLE_SECONDS = 300

_CACHE: dict | None = None
_CACHE_TS = 0.0
_CACHE_COMMAND: str | None = None
_CLIENT: CodexAppServerClient | None = None
_CLIENT_LOCK = threading.Lock()


def read_usage_limits(config: dict | None = None) -> dict:
    config = config or {}
    if config.get("codex_rate_limits_enabled") is False:
        close_codex_account_client()
        return _unavailable("disabled")

    command_issue = _configured_codex_command_issue(config)
    if command_issue:
        close_codex_account_client()
        return _unavailable(command_issue)

    command = _resolve_codex_command(config)
    if not command:
        close_codex_account_client()
        return _unavailable(
            "codex app-server launcher not found; configure codex_app_server_command "
            "with a real Codex launcher such as %USERPROFILE%\\.codex\\bin\\codex.cmd"
        )

    cache_seconds = _safe_int(config.get("codex_rate_limits_cache_seconds"), DEFAULT_CACHE_SECONDS, 0, 300)
    now = time.time()
    global _CACHE, _CACHE_TS, _CACHE_COMMAND
    if cache_seconds > 0 and _CACHE and _CACHE_COMMAND == command and now - _CACHE_TS < cache_seconds:
        cached = dict(_CACHE)
        cached["cached"] = True
        cached["stale"] = False
        return cached

    timeout_seconds = _safe_int(config.get("codex_rate_limits_timeout_seconds"), DEFAULT_TIMEOUT_SECONDS, 3, 60)
    persistent = config.get("codex_rate_limits_persistent") is not False
    idle_seconds = _safe_int(config.get("codex_rate_limits_idle_seconds"), DEFAULT_IDLE_SECONDS, 10, 3600)
    try:
        if persistent:
            result = _shared_client(command, idle_seconds).request_rate_limits(timeout_seconds)
        else:
            close_codex_account_client()
            result = _request_rate_limits_once(command, timeout_seconds)
    except Exception as error:
        return _stale_or_unavailable(command, str(error))

    if result.get("error"):
        return _stale_or_unavailable(command, _error_message(result["error"]))

    snapshot = _normalize_rate_limits(result.get("result") or {})
    snapshot["cached"] = False
    snapshot["stale"] = False
    snapshot["last_success_at"] = snapshot.get("last_success_at") or snapshot.get("fetched_at")
    _CACHE = snapshot
    _CACHE_TS = time.time()
    _CACHE_COMMAND = command
    return snapshot


def _shared_client(command: str, idle_seconds: int) -> CodexAppServerClient:
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None or _CLIENT.command != command or _CLIENT.idle_seconds != idle_seconds:
            old_client = _CLIENT
            _CLIENT = CodexAppServerClient(command, idle_seconds)
            if old_client is not None:
                old_client.close()
        return _CLIENT


def close_codex_account_client() -> None:
    global _CLIENT
    with _CLIENT_LOCK:
        client = _CLIENT
        _CLIENT = None
    if client is not None:
        client.close()


def _resolve_codex_command(config: dict) -> str | None:
    configured = str(config.get("codex_app_server_command") or "").strip()
    if configured:
        return os.path.expandvars(configured)
    return discover_codex_command()


def _configured_codex_command_issue(config: dict) -> str | None:
    configured = str(config.get("codex_app_server_command") or "").strip()
    if not configured:
        return None
    if not is_usable_codex_command(configured):
        return (
            "codex_app_server_command is not a usable local Codex launcher; "
            "point it to a real file such as %USERPROFILE%\\.codex\\bin\\codex.cmd "
            "and avoid WindowsApps aliases"
        )
    return None


def _unavailable(message: str) -> dict:
    return {
        "ok": False,
        "source": "codex_app_server",
        "cached": False,
        "stale": False,
        "error": message,
        "last_success_at": None,
        "windows": [],
    }


def _stale_or_unavailable(command: str, message: str) -> dict:
    stale = _stale_from_cache(command, message)
    if stale:
        return stale
    return _unavailable(message)


def _stale_from_cache(command: str, message: str) -> dict | None:
    if not _CACHE or _CACHE_COMMAND != command:
        return None
    snapshot = dict(_CACHE)
    snapshot["ok"] = True
    snapshot["cached"] = True
    snapshot["stale"] = True
    snapshot["stale_error"] = message
    snapshot["last_success_at"] = snapshot.get("last_success_at") or snapshot.get("fetched_at")
    return snapshot


def _error_message(error) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


atexit.register(close_codex_account_client)
