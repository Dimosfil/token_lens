from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time


DEFAULT_IDLE_SECONDS = 300


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
                stop_process(proc)

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
            stop_process(proc)
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


def request_rate_limits_once(command: str, timeout_seconds: int) -> dict:
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


def stop_process(proc: subprocess.Popen) -> None:
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
