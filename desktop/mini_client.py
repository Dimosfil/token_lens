from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT / "Logo.png"
ICON_PATH = ROOT / "Logo.ico"
DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_LIMIT = 4
DEFAULT_REFRESH_MS = 5000
APP_USER_MODEL_ID = "TokenLens.Mini"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Token Lens mini desktop client")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--refresh-ms", type=int, default=DEFAULT_REFRESH_MS)
    parser.add_argument("--range", dest="range_key", default="")
    return parser.parse_args()


def clamp(value: int, minimum: int, maximum: int) -> int:
    return min(max(value, minimum), maximum)


def format_number(value) -> str:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{number:,}".replace(",", " ")


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 4.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_json(self, path: str, query: dict | None = None):
        url = self._url(path, query)
        with urlopen(url, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, query: dict | None = None):
        request = Request(self._url(path, query), method="POST")
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _url(self, path: str, query: dict | None = None) -> str:
        url = f"{self.base_url}{path}"
        filtered = {
            key: value
            for key, value in (query or {}).items()
            if value not in ("", None)
        }
        if filtered:
            return f"{url}?{urlencode(filtered)}"
        return url


class MiniClientApp:
    def __init__(self, root: tk.Tk, api: ApiClient, limit: int, refresh_ms: int, range_key: str):
        self.root = root
        self.api = api
        self.refresh_ms = clamp(refresh_ms, 1000, 60000)
        self.range_key = range_key
        self.data_version = None
        self.worker_running = False
        self.closed = False
        self.poll_after_id = None
        self.limit_var = tk.IntVar(value=clamp(limit, 1, 50))
        self.status_var = tk.StringVar(value="Loading data")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh(import_first=False)

    def _build_ui(self):
        self.root.title("Token Lens Mini")
        self._set_window_icon()
        self.root.minsize(520, 220)
        self.root.geometry("640x260")

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(toolbar, text="Rows").pack(side=tk.LEFT)
        rows = ttk.Spinbox(
            toolbar,
            from_=1,
            to=50,
            width=4,
            textvariable=self.limit_var,
            command=lambda: self.refresh(import_first=False),
        )
        rows.pack(side=tk.LEFT, padx=(6, 10))
        rows.bind("<Return>", lambda _event: self.refresh(import_first=False))
        rows.bind("<FocusOut>", lambda _event: self.refresh(import_first=False))

        ttk.Button(toolbar, text="Refresh", command=lambda: self.refresh(import_first=True)).pack(side=tk.LEFT)
        ttk.Label(toolbar, textvariable=self.status_var, anchor=tk.E).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        columns = ("model", "calls", "per_call", "total")
        self.table = ttk.Treeview(outer, columns=columns, show="headings", height=self.limit_var.get())
        self.table.heading("model", text="Model")
        self.table.heading("calls", text="Calls")
        self.table.heading("per_call", text="Total / Call")
        self.table.heading("total", text="Total")
        self.table.column("model", width=260, minwidth=160, stretch=True)
        self.table.column("calls", width=70, minwidth=60, anchor=tk.E, stretch=False)
        self.table.column("per_call", width=110, minwidth=95, anchor=tk.E, stretch=False)
        self.table.column("total", width=110, minwidth=90, anchor=tk.E, stretch=False)
        self.table.pack(fill=tk.BOTH, expand=True)

    def _set_window_icon(self):
        if ICON_PATH.exists():
            try:
                self.root.iconbitmap(default=str(ICON_PATH))
                return
            except tk.TclError:
                pass
        if not LOGO_PATH.exists():
            return
        try:
            self.logo_icon = tk.PhotoImage(file=str(LOGO_PATH))
            self.root.iconphoto(True, self.logo_icon)
        except tk.TclError:
            self.logo_icon = None

    def close(self):
        self.closed = True
        if self.poll_after_id is not None:
            self.root.after_cancel(self.poll_after_id)
            self.poll_after_id = None
        self.root.destroy()

    def schedule_poll(self):
        if not self.closed:
            if self.poll_after_id is not None:
                self.root.after_cancel(self.poll_after_id)
            self.poll_after_id = self.root.after(self.refresh_ms, self.poll_for_updates)

    def poll_for_updates(self):
        self.poll_after_id = None
        if self.worker_running:
            self.schedule_poll()
            return
        self._run_worker(self._poll_worker)

    def refresh(self, import_first: bool = False):
        if self.worker_running:
            return
        if self.poll_after_id is not None:
            self.root.after_cancel(self.poll_after_id)
            self.poll_after_id = None
        self.status_var.set("Importing data" if import_first else "Loading data")
        self._run_worker(lambda: self._refresh_worker(import_first))

    def _run_worker(self, target):
        self.worker_running = True
        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def _poll_worker(self):
        try:
            state = self.api.get_json("/api/state")
            if self.data_version is None or state.get("version") != self.data_version:
                rows = self.load_rows()
                self._ui(lambda: self.render_rows(rows, state.get("version")))
            else:
                self._ui(lambda: self.set_checked_status())
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self._ui(lambda: self.set_error(error))
        finally:
            self._ui(self._finish_worker)

    def _refresh_worker(self, import_first: bool):
        try:
            if import_first:
                dashboard = self.api.post_json("/api/refresh", self.query())
                rows = dashboard.get("tasks", [])
                version = dashboard.get("state", {}).get("version")
            else:
                rows = self.load_rows()
                version = self.api.get_json("/api/state").get("version")
            self._ui(lambda: self.render_rows(rows, version))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self._ui(lambda: self.set_error(error))
        finally:
            self._ui(self._finish_worker)

    def _finish_worker(self):
        self.worker_running = False
        self.schedule_poll()

    def _ui(self, callback):
        if not self.closed:
            self.root.after(0, callback)

    def query(self) -> dict:
        return {"limit": self.current_limit(), "range": self.range_key}

    def load_rows(self) -> list[dict]:
        return self.api.get_json("/api/tasks", self.query())

    def current_limit(self) -> int:
        try:
            value = self.limit_var.get()
        except tk.TclError:
            value = DEFAULT_LIMIT
            self.limit_var.set(value)
        value = clamp(value, 1, 50)
        if self.limit_var.get() != value:
            self.limit_var.set(value)
        return value

    def render_rows(self, rows: list[dict], version):
        self.data_version = version
        self.table.configure(height=self.current_limit())
        for item in self.table.get_children():
            self.table.delete(item)
        for row in rows[: self.current_limit()]:
            self.table.insert(
                "",
                tk.END,
                values=(
                    row.get("models") or "",
                    format_number(row.get("model_calls")),
                    format_number(row.get("total_tokens_per_call")),
                    format_number(row.get("total_tokens")),
                ),
            )
        self.status_var.set(f"Updated {time.strftime('%H:%M:%S')}")

    def set_checked_status(self):
        self.status_var.set(f"Checked {time.strftime('%H:%M:%S')}")

    def set_error(self, error: Exception):
        self.status_var.set(f"Error: {error}")


def main():
    args = parse_args()
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    app = MiniClientApp(
        root,
        ApiClient(args.base_url),
        args.limit,
        args.refresh_ms,
        args.range_key,
    )
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
