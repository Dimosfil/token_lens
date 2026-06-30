from __future__ import annotations

import atexit
from datetime import datetime, timezone
import json
import os
import queue
import subprocess
import threading
import time

from app.core.codex_discovery import discover_codex_command, is_usable_codex_command


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
        return _unavailable(str(error))

    if result.get("error"):
        return _unavailable(_error_message(result["error"]))

    snapshot = _normalize_rate_limits(result.get("result") or {})
    _CACHE = snapshot
    _CACHE_TS = time.time()
    _CACHE_COMMAND = command
    return snapshot


class CodexAppServerClient:
    def __init__(self, command: str, idle_seconds: int = DEFAULT_IDLE_SECONDS):
        self.command = command
        self.idle_seconds = idle_seconds
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue[str | None] | None = None
        self.reader: threading.Thread | None = None
        self.initialized = False
        self.next_id = 1
        self.last_used = 0.0
        self.lock = threading.RLock()

    def request_rate_limits(self, timeout_seconds: int) -> dict:
        with self.lock:
            self._close_if_idle()
            self._ensure_initialized(timeout_seconds)
            request_id = self._next_message_id()
            try:
                _write_message(self._require_proc(), {
                    "id": request_id,
                    "method": "account/rateLimits/read",
                    "params": None,
                })
                message = self._wait_for_message(request_id, timeout_seconds)
            except Exception:
                self.close()
                raise
            self.last_used = time.time()
            return message

    def close(self) -> None:
        with self.lock:
            proc = self.proc
            self.proc = None
            self.lines = None
            self.reader = None
            self.initialized = False
            if proc is not None:
                _stop_process(proc)

    def _ensure_initialized(self, timeout_seconds: int) -> None:
        proc = self._current_live_process()
        if proc is None:
            self._start_process()
            proc = self._require_proc()
        if self.initialized:
            return

        initialize_id = self._next_message_id()
        try:
            _write_message(proc, {
                "id": initialize_id,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "token_lens",
                        "title": "Token Lens",
                        "version": "0.1.0",
                    },
                },
            })
            self._wait_for_message(initialize_id, timeout_seconds)
            _write_message(proc, {"method": "initialized", "params": {}})
        except Exception:
            self.close()
            raise
        self.initialized = True
        self.last_used = time.time()

    def _start_process(self) -> None:
        creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        proc = subprocess.Popen(
            [self.command, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=creation_flags,
        )
        lines: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(target=_read_stdout_lines, args=(proc, lines), daemon=True)
        reader.start()
        self.proc = proc
        self.lines = lines
        self.reader = reader
        self.initialized = False

    def _wait_for_message(self, message_id: int, timeout_seconds: int) -> dict:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            remaining = max(0.0, deadline - time.time())
            try:
                line = self._require_lines().get(timeout=min(0.25, remaining))
            except queue.Empty:
                proc = self._current_live_process()
                if proc is None:
                    raise RuntimeError("codex app-server exited before replying")
                continue
            if line is None:
                raise RuntimeError("codex app-server closed stdout before replying")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == message_id:
                return message
        raise TimeoutError("codex app-server rate limit request timed out")

    def _close_if_idle(self) -> None:
        if self.proc is None or self.idle_seconds <= 0 or self.last_used <= 0:
            return
        if time.time() - self.last_used > self.idle_seconds:
            self.close()

    def _current_live_process(self) -> subprocess.Popen | None:
        if self.proc is None:
            return None
        if self.proc.poll() is not None:
            proc = self.proc
            self.proc = None
            self.lines = None
            self.reader = None
            self.initialized = False
            _stop_process(proc)
            return None
        return self.proc

    def _require_proc(self) -> subprocess.Popen:
        proc = self.proc
        if proc is None:
            raise RuntimeError("codex app-server process is unavailable")
        return proc

    def _require_lines(self) -> queue.Queue[str | None]:
        lines = self.lines
        if lines is None:
            raise RuntimeError("codex app-server stdout reader is unavailable")
        return lines

    def _next_message_id(self) -> int:
        message_id = self.next_id
        self.next_id += 1
        return message_id


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


def _request_rate_limits_once(command: str, timeout_seconds: int) -> dict:
    client = CodexAppServerClient(command, idle_seconds=0)
    try:
        return client.request_rate_limits(timeout_seconds)
    except TimeoutError as error:
        return {"error": {"message": str(error)}}
    finally:
        client.close()


def _read_stdout_lines(proc: subprocess.Popen, lines: queue.Queue[str | None]) -> None:
    if proc.stdout is None:
        lines.put(None)
        return
    for line in proc.stdout:
        lines.put(line.strip())
    lines.put(None)


def _write_message(proc: subprocess.Popen, message: dict) -> None:
    if proc.stdin is None:
        raise RuntimeError("codex app-server stdin is unavailable")
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _stop_process(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        _stop_windows_process_tree(proc)
        return

    if proc.poll() is not None:
        return
    proc.kill()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _stop_windows_process_tree(proc: subprocess.Popen) -> None:
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=5,
    )
    if proc.poll() is not None:
        return
    proc.kill()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _normalize_rate_limits(result: dict) -> dict:
    primary_snapshot = result.get("rateLimits") or {}
    buckets = result.get("rateLimitsByLimitId") or {}
    now = int(time.time())
    snapshots = []
    if isinstance(buckets, dict) and buckets:
        for limit_id in sorted(buckets):
            snapshot = buckets.get(limit_id)
            if isinstance(snapshot, dict):
                snapshots.append(snapshot)
    elif isinstance(primary_snapshot, dict) and primary_snapshot:
        snapshots.append(primary_snapshot)

    groups = [_normalize_limit_group(snapshot, now) for snapshot in snapshots]
    groups = [group for group in groups if group["windows"]]
    windows = [window for group in groups for window in group["windows"]]
    snapshot = primary_snapshot if isinstance(primary_snapshot, dict) else {}
    return {
        "ok": True,
        "source": "codex_app_server",
        "cached": False,
        "fetched_at": _iso_from_ts(now),
        "limit_id": snapshot.get("limitId"),
        "limit_name": snapshot.get("limitName"),
        "plan_type": snapshot.get("planType"),
        "rate_limit_reached_type": snapshot.get("rateLimitReachedType"),
        "credits": snapshot.get("credits"),
        "groups": groups,
        "windows": windows,
        "limit_ids": sorted(buckets.keys()),
    }


def _normalize_limit_group(snapshot: dict, now: int) -> dict:
    limit_id = snapshot.get("limitId")
    limit_name = snapshot.get("limitName")
    display_name = str(limit_name or "Codex")
    windows = []
    for key, fallback_label in (("primary", "5h"), ("secondary", "weekly")):
        window = snapshot.get(key)
        if isinstance(window, dict):
            windows.append(_normalize_window(
                key,
                fallback_label,
                window,
                now,
                str(limit_id or ""),
                str(limit_name or ""),
                display_name,
            ))
    return {
        "limit_id": limit_id,
        "limit_name": limit_name,
        "display_name": display_name,
        "plan_type": snapshot.get("planType"),
        "rate_limit_reached_type": snapshot.get("rateLimitReachedType"),
        "credits": snapshot.get("credits"),
        "windows": windows,
    }


def _normalize_window(
    key: str,
    fallback_label: str,
    window: dict,
    now: int,
    limit_id: str,
    limit_name: str,
    display_name: str,
) -> dict:
    used_percent = _safe_int(window.get("usedPercent"), 0, 0, 100)
    reset_ts = window.get("resetsAt")
    reset_seconds = None
    reset_at = None
    if isinstance(reset_ts, int):
        reset_seconds = max(0, reset_ts - now)
        reset_at = _iso_from_ts(reset_ts)
    duration_mins = window.get("windowDurationMins")
    return {
        "key": key,
        "limit_id": limit_id,
        "limit_name": limit_name,
        "display_name": display_name,
        "label": _window_label(duration_mins, fallback_label),
        "window_duration_mins": duration_mins,
        "used_percent": used_percent,
        "remaining_percent": max(0, min(100, 100 - used_percent)),
        "reset_at": reset_at,
        "reset_seconds": reset_seconds,
    }


def _window_label(duration_mins, fallback: str) -> str:
    if duration_mins == 300:
        return "5h"
    if duration_mins == 10080:
        return "weekly"
    if isinstance(duration_mins, int) and duration_mins >= 60 and duration_mins % 60 == 0:
        return f"{duration_mins // 60}h"
    return fallback


def _iso_from_ts(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _safe_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def _unavailable(message: str) -> dict:
    return {
        "ok": False,
        "source": "codex_app_server",
        "cached": False,
        "error": message,
        "windows": [],
    }


def _error_message(error) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


atexit.register(close_codex_account_client)
