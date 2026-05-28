from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import ttk
try:
    import winsound
except ImportError:
    winsound = None
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT / "Logo.png"
ICON_PATH = ROOT / "Logo.ico"
SETTINGS_PATH = ROOT / "data" / "mini_settings.json"
DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_LIMIT = 4
DEFAULT_REFRESH_MS = 5000
DEFAULT_SIGNAL_THRESHOLD = 100000
APP_USER_MODEL_ID = "TokenLens.Mini.CleanLogo"
FLASHW_STOP = 0
FLASHW_CAPTION = 0x00000001
FLASHW_TRAY = 0x00000002
FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY
FLASHW_TIMERNOFG = 0x0000000C
SIGNAL_CHOICES = {
    "Simple": -1,
    "Asterisk": 0x00000040,
    "Exclamation": 0x00000030,
    "Hand": 0x00000010,
    "Question": 0x00000020,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Token Lens mini desktop client")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--refresh-ms", type=int, default=DEFAULT_REFRESH_MS)
    parser.add_argument("--range", dest="range_key", default="")
    parser.add_argument("--signal-threshold", type=int, default=DEFAULT_SIGNAL_THRESHOLD)
    parser.add_argument("--signal", choices=SIGNAL_CHOICES.keys(), default="Exclamation")
    parser.add_argument("--signal-enabled", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def clamp(value: int, minimum: int, maximum: int) -> int:
    return min(max(value, minimum), maximum)


def format_number(value) -> str:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{number:,}".replace(",", " ")


def parse_int(value, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def load_mini_settings() -> dict:
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_mini_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = SETTINGS_PATH.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(settings, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(SETTINGS_PATH)


def setting_int(settings: dict, key: str, default: int, minimum: int, maximum: int) -> int:
    return clamp(parse_int(settings.get(key), default), minimum, maximum)


def setting_bool(settings: dict, key: str, default: bool) -> bool:
    value = settings.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def setting_str(settings: dict, key: str, default: str) -> str:
    value = settings.get(key, default)
    return value if isinstance(value, str) else default


class FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hwnd", ctypes.c_void_p),
        ("dwFlags", ctypes.c_uint),
        ("uCount", ctypes.c_uint),
        ("dwTimeout", ctypes.c_uint),
    ]


def format_duration(seconds) -> str:
    try:
        total_seconds = max(0, int(seconds or 0))
    except (TypeError, ValueError):
        total_seconds = 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes}:{remaining_seconds:02d}"


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
    def __init__(
        self,
        root: tk.Tk,
        api: ApiClient,
        limit: int,
        refresh_ms: int,
        range_key: str,
        signal_threshold: int,
        signal_name: str,
        signal_enabled: bool,
        settings: dict | None = None,
    ):
        self.root = root
        self.api = api
        self.settings = settings or {}
        self.refresh_ms = clamp(refresh_ms, 1000, 60000)
        self.range_key = range_key
        self.data_version = None
        self.worker_running = False
        self.closed = False
        self.poll_after_id = None
        self.settings_after_id = None
        self.last_signal_key = None
        self.limit_var = tk.IntVar(value=clamp(limit, 1, 50))
        self.signal_enabled_var = tk.BooleanVar(value=signal_enabled)
        self.signal_threshold_var = tk.IntVar(value=max(0, signal_threshold))
        self.signal_name_var = tk.StringVar(
            value=signal_name if signal_name in SIGNAL_CHOICES else "Exclamation"
        )
        self.status_var = tk.StringVar(value="Loading data")

        self._build_ui()
        self._bind_settings_persistence()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh(import_first=False)

    def _build_ui(self):
        self.root.title("Token Lens Mini")
        self._set_window_icon()
        self.root.minsize(620, 220)
        geometry = setting_str(self.settings, "geometry", "720x260")
        try:
            self.root.geometry(geometry)
        except tk.TclError:
            self.root.geometry("720x260")

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
        ttk.Checkbutton(toolbar, text="Signal", variable=self.signal_enabled_var).pack(side=tk.LEFT, padx=(10, 4))
        ttk.Spinbox(
            toolbar,
            from_=0,
            to=10000000,
            increment=1000,
            width=8,
            textvariable=self.signal_threshold_var,
        ).pack(side=tk.LEFT, padx=(0, 4))
        signal_picker = ttk.Combobox(
            toolbar,
            width=11,
            state="readonly",
            values=tuple(SIGNAL_CHOICES.keys()),
            textvariable=self.signal_name_var,
        )
        signal_picker.pack(side=tk.LEFT)
        signal_picker.bind("<<ComboboxSelected>>", lambda _event: self.play_signal())
        ttk.Label(toolbar, textvariable=self.status_var, anchor=tk.E).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        columns = ("model", "time", "calls", "per_call", "total")
        self.table = ttk.Treeview(outer, columns=columns, show="headings", height=self.limit_var.get())
        self.table.heading("model", text="Model")
        self.table.heading("time", text="Time")
        self.table.heading("calls", text="Calls")
        self.table.heading("per_call", text="Total / Call")
        self.table.heading("total", text="Total")
        self.table.column("model", width=220, minwidth=150, stretch=True)
        self.table.column("time", width=80, minwidth=70, anchor=tk.E, stretch=False)
        self.table.column("calls", width=70, minwidth=60, anchor=tk.E, stretch=False)
        self.table.column("per_call", width=110, minwidth=95, anchor=tk.E, stretch=False)
        self.table.column("total", width=110, minwidth=90, anchor=tk.E, stretch=False)
        self.table.pack(fill=tk.BOTH, expand=True)

    def _bind_settings_persistence(self):
        for variable in (
            self.limit_var,
            self.signal_enabled_var,
            self.signal_threshold_var,
            self.signal_name_var,
        ):
            variable.trace_add("write", lambda *_args: self.schedule_settings_save())
        self.root.bind("<Configure>", lambda _event: self.schedule_settings_save(), add="+")

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
        if self.settings_after_id is not None:
            self.root.after_cancel(self.settings_after_id)
            self.settings_after_id = None
        self.save_settings_now()
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

    def schedule_settings_save(self):
        if self.closed:
            return
        if self.settings_after_id is not None:
            self.root.after_cancel(self.settings_after_id)
        self.settings_after_id = self.root.after(400, self.save_settings_now)

    def save_settings_now(self):
        self.settings_after_id = None
        snapshot = {
            **self.settings,
            "base_url": self.api.base_url,
            "limit": self.read_int_var(self.limit_var, DEFAULT_LIMIT, 1, 50),
            "refresh_ms": self.refresh_ms,
            "range": self.range_key,
            "signal_enabled": self.read_bool_var(self.signal_enabled_var, True),
            "signal_threshold": self.read_int_var(
                self.signal_threshold_var,
                DEFAULT_SIGNAL_THRESHOLD,
                0,
                10000000,
            ),
            "signal": self.read_signal_name(),
            "geometry": self.root.geometry(),
        }
        try:
            save_mini_settings(snapshot)
            self.settings = snapshot
        except OSError:
            pass

    def read_int_var(self, variable: tk.IntVar, default: int, minimum: int, maximum: int) -> int:
        try:
            value = variable.get()
        except tk.TclError:
            value = default
        return clamp(value, minimum, maximum)

    def read_bool_var(self, variable: tk.BooleanVar, default: bool) -> bool:
        try:
            return bool(variable.get())
        except tk.TclError:
            return default

    def read_signal_name(self) -> str:
        signal_name = self.signal_name_var.get()
        return signal_name if signal_name in SIGNAL_CHOICES else "Exclamation"

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
                    format_duration(row.get("elapsed_seconds")),
                    format_number(row.get("model_calls")),
                    format_number(row.get("total_tokens_per_call")),
                    format_number(row.get("total_tokens")),
                ),
            )
        self.maybe_signal(rows, version)
        self.status_var.set(f"Updated {time.strftime('%H:%M:%S')}")

    def set_checked_status(self):
        self.status_var.set(f"Checked {time.strftime('%H:%M:%S')}")

    def set_error(self, error: Exception):
        self.status_var.set(f"Error: {error}")

    def current_signal_threshold(self) -> int:
        try:
            value = self.signal_threshold_var.get()
        except tk.TclError:
            value = DEFAULT_SIGNAL_THRESHOLD
            self.signal_threshold_var.set(value)
        value = max(0, value)
        if self.signal_threshold_var.get() != value:
            self.signal_threshold_var.set(value)
        return value

    def maybe_signal(self, rows: list[dict], version):
        if not self.signal_enabled_var.get():
            return
        threshold = self.current_signal_threshold()
        if threshold <= 0:
            return
        over_limit = [
            parse_int(row.get("total_tokens_per_call"))
            for row in rows[: self.current_limit()]
            if parse_int(row.get("total_tokens_per_call")) > threshold
        ]
        if not over_limit:
            return
        signal_key = (version, threshold, self.signal_name_var.get(), max(over_limit))
        if signal_key == self.last_signal_key:
            return
        self.last_signal_key = signal_key
        self.play_signal()

    def play_signal(self):
        signal_name = self.signal_name_var.get()
        if winsound is not None:
            try:
                winsound.MessageBeep(SIGNAL_CHOICES.get(signal_name, -1))
                self.flash_window()
                return
            except RuntimeError:
                pass
        try:
            self.root.bell()
        except tk.TclError:
            pass
        self.flash_window()

    def flash_window(self):
        try:
            hwnd = self.root.winfo_id()
            info = FLASHWINFO(
                ctypes.sizeof(FLASHWINFO),
                hwnd,
                FLASHW_ALL | FLASHW_TIMERNOFG,
                5,
                0,
            )
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
        except (AttributeError, OSError, tk.TclError):
            pass


def main():
    args = parse_args()
    settings = load_mini_settings()
    base_url = setting_str(settings, "base_url", args.base_url)
    limit = setting_int(settings, "limit", args.limit, 1, 50)
    refresh_ms = setting_int(settings, "refresh_ms", args.refresh_ms, 1000, 60000)
    range_key = setting_str(settings, "range", args.range_key)
    signal_threshold = setting_int(
        settings,
        "signal_threshold",
        args.signal_threshold,
        0,
        10000000,
    )
    signal_name = setting_str(settings, "signal", args.signal)
    if signal_name not in SIGNAL_CHOICES:
        signal_name = args.signal
    signal_enabled = setting_bool(settings, "signal_enabled", args.signal_enabled)
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    app = MiniClientApp(
        root,
        ApiClient(base_url),
        limit,
        refresh_ms,
        range_key,
        signal_threshold,
        signal_name,
        signal_enabled,
        settings,
    )
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
