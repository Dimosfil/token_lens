from __future__ import annotations

import argparse
import ctypes
from datetime import datetime
import json
import logging
from pathlib import Path
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
try:
    import winsound
except ImportError:
    winsound = None
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging_config import configure_logging
LOGO_PATH = ROOT / "Logo.png"
ICON_PATH = ROOT / "Logo.ico"
SETTINGS_PATH = ROOT / "data" / "mini_settings.json"
SERVER_SCRIPT_PATH = ROOT / "run_server.py"
SERVER_PID_PATH = ROOT / "data" / "server.pid"
SERVER_OUT_LOG_PATH = ROOT / "data" / "server.out.log"
SERVER_ERR_LOG_PATH = ROOT / "data" / "server.err.log"
DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_LIMIT = 4
DEFAULT_REFRESH_MS = 5000
DEFAULT_SIGNAL_THRESHOLD = 100000
DEFAULT_SOURCE = "codex"
SOURCE_CHOICES = (
    ("Codex", "codex"),
    ("OpenCode", "opencode"),
)
LIMIT_BAR_HEIGHT = 12
LIMIT_BAR_TRACK_COLOR = "#e7ebef"
LIMIT_BAR_BORDER_COLOR = "#a8b0b7"
LIMIT_BAR_MARKER_COLOR = "#2f3a40"
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
LOCAL_API_HOSTS = {"127.0.0.1", "localhost", "::1"}
SERVER_START_TIMEOUT_SECONDS = 15
SERVER_START_RETRY_SECONDS = 20
LOGGER = logging.getLogger("token_lens.mini")
TABLE_COLUMNS = (
    {"id": "date", "label": "Date", "width": 90, "minwidth": 82, "anchor": tk.W, "stretch": False},
    {"id": "date_time", "label": "Date/time", "width": 130, "minwidth": 118, "anchor": tk.W, "stretch": False},
    {"id": "task", "label": "Project / task", "width": 260, "minwidth": 170, "anchor": tk.W, "stretch": True},
    {"id": "models", "label": "Models", "width": 140, "minwidth": 100, "anchor": tk.W, "stretch": False},
    {"id": "time", "label": "Time", "width": 80, "minwidth": 70, "anchor": tk.E, "stretch": False},
    {"id": "calls", "label": "Calls", "width": 70, "minwidth": 60, "anchor": tk.E, "stretch": False},
    {"id": "per_call", "label": "Total / Call", "width": 110, "minwidth": 95, "anchor": tk.E, "stretch": False},
    {"id": "total", "label": "Total", "width": 110, "minwidth": 90, "anchor": tk.E, "stretch": False},
    {"id": "cost", "label": "Cost", "width": 80, "minwidth": 70, "anchor": tk.E, "stretch": False},
)
TABLE_COLUMN_IDS = tuple(column["id"] for column in TABLE_COLUMNS)
DEFAULT_VISIBLE_COLUMNS = TABLE_COLUMN_IDS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Token Lens mini desktop client")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--refresh-ms", type=int, default=DEFAULT_REFRESH_MS)
    parser.add_argument("--range", dest="range_key", default="")
    parser.add_argument("--source", choices=[value for _label, value in SOURCE_CHOICES], default=DEFAULT_SOURCE)
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


def format_cost(value) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"${amount:.4f}"


def parse_int(value, default: int = 0) -> int:
    try:
        return int(default if value in (None, "") else value)
    except (TypeError, ValueError):
        return default


def load_mini_settings() -> dict:
    settings, _save_enabled = load_mini_settings_with_status()
    return settings


def load_mini_settings_with_status() -> tuple[dict, bool]:
    try:
        return _read_mini_settings_file(SETTINGS_PATH), True
    except FileNotFoundError:
        return {}, True
    except OSError:
        settings = _load_backup_mini_settings()
        return (settings, True) if settings is not None else ({}, False)
    except (json.JSONDecodeError, ValueError):
        settings = _load_backup_mini_settings()
        if settings is not None:
            _repair_mini_settings(settings)
            return settings, True
        _preserve_corrupt_mini_settings()
        return {}, True


def _read_mini_settings_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("mini settings root must be an object")
    return data


def _mini_settings_backup_path() -> Path:
    return SETTINGS_PATH.with_name(f"{SETTINGS_PATH.name}.bak")


def _load_backup_mini_settings() -> dict | None:
    try:
        return _read_mini_settings_file(_mini_settings_backup_path())
    except (FileNotFoundError, OSError, json.JSONDecodeError, ValueError):
        return None


def _repair_mini_settings(settings: dict) -> None:
    try:
        save_mini_settings(settings)
    except OSError:
        pass


def _preserve_corrupt_mini_settings() -> None:
    if not SETTINGS_PATH.exists():
        return
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    corrupt_path = SETTINGS_PATH.with_name(f"{SETTINGS_PATH.name}.corrupt-{timestamp}")
    try:
        SETTINGS_PATH.replace(corrupt_path)
    except OSError:
        pass


def save_mini_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(SETTINGS_PATH, settings)
    _write_json_atomic(_mini_settings_backup_path(), settings)


def _write_json_atomic(path: Path, settings: dict) -> None:
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(settings, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


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


def setting_columns(settings: dict, key: str = "columns") -> tuple[str, ...]:
    return normalize_table_columns(settings.get(key))


def source_settings(settings: dict, source: str) -> dict:
    agents = settings.get("agents")
    if not isinstance(agents, dict):
        return {}
    source_config = agents.get(normalize_source(source))
    return source_config if isinstance(source_config, dict) else {}


def setting_int_for_source(
    settings: dict,
    source: str,
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    source_config = source_settings(settings, source)
    return setting_int(source_config, key, setting_int(settings, key, default, minimum, maximum), minimum, maximum)


def setting_bool_for_source(settings: dict, source: str, key: str, default: bool) -> bool:
    source_config = source_settings(settings, source)
    return setting_bool(source_config, key, setting_bool(settings, key, default))


def setting_str_for_source(settings: dict, source: str, key: str, default: str) -> str:
    source_config = source_settings(settings, source)
    return setting_str(source_config, key, setting_str(settings, key, default))


def setting_columns_for_source(settings: dict, source: str) -> tuple[str, ...]:
    source_config = source_settings(settings, source)
    if "columns" in source_config:
        return setting_columns(source_config)
    return setting_columns(settings)


def normalize_table_columns(value) -> tuple[str, ...]:
    if isinstance(value, str):
        candidates = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple)):
        candidates = [str(item).strip() for item in value]
    else:
        return DEFAULT_VISIBLE_COLUMNS

    seen = set()
    columns = []
    for column_id in candidates:
        if column_id in TABLE_COLUMN_IDS and column_id not in seen:
            seen.add(column_id)
            columns.append(column_id)
    return tuple(columns) if columns else DEFAULT_VISIBLE_COLUMNS


def normalize_source(value) -> str:
    text = str(value or "").strip().lower()
    return text if text in {source for _label, source in SOURCE_CHOICES} else DEFAULT_SOURCE


def is_local_api_url(base_url: str) -> bool:
    try:
        parsed = urlparse(base_url)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in LOCAL_API_HOSTS


def is_connection_refused(error: Exception) -> bool:
    candidates = [error]
    reason = getattr(error, "reason", None)
    if isinstance(reason, BaseException):
        candidates.append(reason)
    context = getattr(error, "__context__", None)
    if isinstance(context, BaseException):
        candidates.append(context)

    for candidate in candidates:
        if getattr(candidate, "winerror", None) == 10061:
            return True
        if getattr(candidate, "errno", None) in {61, 111, 10061}:
            return True
        text = str(candidate).lower()
        if "10061" in text or "connection refused" in text or "подключение не установлено" in text:
            return True
    return False


def python_for_server() -> str:
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        python_exe = executable.with_name("python.exe")
        if python_exe.exists():
            return str(python_exe)
    return str(executable)


def start_local_server_process() -> subprocess.Popen:
    if not SERVER_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Cannot find {SERVER_SCRIPT_PATH}")
    SERVER_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    stdout = SERVER_OUT_LOG_PATH.open("ab")
    stderr = SERVER_ERR_LOG_PATH.open("ab")
    try:
        process = subprocess.Popen(
            [python_for_server(), str(SERVER_SCRIPT_PATH)],
            cwd=str(ROOT),
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            close_fds=False,
            creationflags=creationflags,
        )
    finally:
        stdout.close()
        stderr.close()
    SERVER_PID_PATH.write_text(str(process.pid), encoding="ascii")
    LOGGER.info("local server process started pid=%s", process.pid)
    return process


def wait_for_api(api: "ApiClient", timeout_seconds: int = SERVER_START_TIMEOUT_SECONDS) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            api.get_json("/api/state")
            return True
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            time.sleep(0.5)
    return False


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


def looks_like_id(value) -> bool:
    text = str(value or "")
    if len(text) < 12:
        return False
    return all(char.isalnum() or char in {"_", "-"} for char in text)


def task_name(row: dict) -> str:
    name = str(row.get("thread_name") or "").strip()
    if name and not looks_like_id(name):
        return name
    return fallback_task_name(row)


def fallback_task_name(row: dict) -> str:
    period = str(row.get("period") or row.get("day") or "").strip()
    if period:
        return period
    return f"Задача {format_timestamp(row.get('started_at') or row.get('finished_at'))}"


def row_date(row: dict) -> str:
    return format_date(row.get("finished_at") or row.get("started_at") or row.get("ts_iso") or row.get("day"))


def row_datetime(row: dict) -> str:
    return format_timestamp(row.get("finished_at") or row.get("started_at") or row.get("ts_iso") or row.get("day"))


def format_date(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        timestamp = datetime.fromisoformat(text)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone()
        return timestamp.strftime("%Y-%m-%d")
    except ValueError:
        pass
    return text[:10]


def table_cell_value(column_id: str, row: dict) -> str:
    has_usage = row.get("has_usage", 1) not in (0, False)
    if column_id == "date":
        return row_date(row)
    if column_id == "date_time":
        return row_datetime(row)
    if column_id == "task":
        return task_name(row)
    if column_id == "models":
        return row.get("models") or ""
    if column_id == "time":
        return format_duration(row.get("elapsed_seconds"))
    if column_id == "calls":
        return format_number(row.get("model_calls")) if has_usage else "-"
    if column_id == "per_call":
        return format_number(row.get("total_tokens_per_call")) if has_usage else "-"
    if column_id == "total":
        return format_number(row.get("total_tokens")) if has_usage else "-"
    if column_id == "cost":
        return format_cost(row.get("estimated_cost")) if has_usage else "-"
    return ""


def format_timestamp(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        timestamp = datetime.fromisoformat(text)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone()
        return timestamp.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        pass
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        return f"{date_part} {time_part[:5]}"
    return text[:16]


def format_limit_reset(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        reset_at = datetime.fromisoformat(text)
        local_reset = reset_at.astimezone()
    except ValueError:
        return text[:16]
    now = datetime.now(local_reset.tzinfo)
    if local_reset.date() == now.date():
        return local_reset.strftime("%H:%M")
    return local_reset.strftime("%d.%m %H:%M")


def limit_period(row: dict) -> str:
    label = str(row.get("label") or row.get("key") or "").strip()
    if label == "weekly":
        return "week"
    return label or "-"


def usage_limit_name(row: dict) -> str:
    display_name = str(row.get("display_name") or "Codex").strip()
    if display_name == "Codex":
        return "Codex"
    if "Spark" in display_name:
        return "Spark"
    return display_name


def limit_display_name(item: dict) -> str:
    display_name = str(
        item.get("display_name")
        or item.get("limit_name")
        or item.get("limit_id")
        or "Codex"
    ).strip()
    return display_name or "Codex"


def usage_limit_sort_key(group: dict) -> tuple[int, str]:
    name = usage_limit_name(group)
    if name == "Codex":
        return (0, name)
    if name == "Spark":
        return (1, name)
    return (2, name)


def usage_limit_groups(snapshot: dict | None) -> list[dict]:
    if not isinstance(snapshot, dict) or not snapshot.get("ok"):
        return []

    source_groups = snapshot.get("groups")
    groups = []
    if isinstance(source_groups, list):
        for group in source_groups:
            if not isinstance(group, dict):
                continue
            source_windows = group.get("windows")
            windows = [row for row in source_windows if isinstance(row, dict)] if isinstance(source_windows, list) else []
            if windows:
                groups.append({**group, "display_name": limit_display_name(group), "windows": windows})
    if groups:
        return sorted(groups, key=usage_limit_sort_key)

    windows = snapshot.get("windows")
    if not isinstance(windows, list):
        return []
    buckets: dict[tuple[str, str], dict] = {}
    for row in windows:
        if not isinstance(row, dict):
            continue
        display_name = limit_display_name(row)
        key = (str(row.get("limit_id") or ""), display_name)
        buckets.setdefault(key, {"display_name": display_name, "windows": []})["windows"].append(row)
    return sorted(buckets.values(), key=usage_limit_sort_key)


def limit_remaining_percent(row: dict):
    try:
        return clamp(int(row.get("remaining_percent")), 0, 100)
    except (TypeError, ValueError):
        return None


def limit_bar_fill_color(percent: int | None) -> str:
    if percent is None:
        return "#8d989f"
    if percent >= 100:
        return "#1d8f45"
    if percent >= 50:
        return "#0f7c80"
    if percent >= 20:
        return "#c87900"
    return "#b3261e"


def usage_limits_text(snapshot: dict | None) -> str:
    if not isinstance(snapshot, dict):
        return "Limits: unavailable"
    if not snapshot.get("ok"):
        return f"Limits: {snapshot.get('error') or 'unavailable'}"
    windows = snapshot.get("windows")
    if not isinstance(windows, list) or not windows:
        return "Limits: unavailable"
    lines = []
    for row in windows:
        if not isinstance(row, dict):
            continue
        remaining = row.get("remaining_percent")
        reset = format_limit_reset(row.get("reset_at"))
        suffix = f", reset {reset}" if reset else ""
        lines.append(f"{usage_limit_name(row)} {limit_period(row)}: {remaining}% left{suffix}")
    return "\n".join(lines) if lines else "Limits: unavailable"


def import_status_error_text(status: dict | None) -> str:
    if not isinstance(status, dict):
        return ""
    error = str(status.get("error") or "").strip()
    if not error:
        return ""
    return f"Import error: {error}"


def refresh_status_text(status: dict | None, warnings: list | None = None) -> str:
    error_text = import_status_error_text(status)
    if error_text:
        return error_text
    if isinstance(warnings, list) and warnings:
        warning = str(warnings[0]).strip()
        if warning:
            return f"Import warning: {warning}"
    return ""


def backend_status_text(state: str, detail: str) -> str:
    labels = {
        "online": "Backend online",
        "busy": "Backend busy",
        "offline": "Backend offline",
    }
    label = labels.get(state, labels["online"])
    detail = str(detail or "").strip()
    return f"{label} · {detail}" if detail else label


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
        source: str,
        signal_threshold: int,
        signal_name: str,
        signal_enabled: bool,
        settings: dict | None = None,
        settings_save_enabled: bool = True,
    ):
        self.root = root
        self.api = api
        self.settings = settings or {}
        self.settings_save_enabled = settings_save_enabled
        self.settings_save_ready = False
        self.refresh_ms = clamp(refresh_ms, 1000, 60000)
        self.range_key = range_key
        self.data_version = None
        self.active_source = normalize_source(source)
        self.worker_running = False
        self.closed = False
        self.poll_after_id = None
        self.settings_after_id = None
        self.last_server_start_attempt = 0.0
        self.seen_signal_rows = set()
        self.signal_seen_initialized = False
        self.last_signal_key = None
        self.default_limit = clamp(limit, 1, 50)
        self.default_signal_threshold = max(0, signal_threshold)
        self.default_signal_name = signal_name if signal_name in SIGNAL_CHOICES else "Exclamation"
        self.default_signal_enabled = signal_enabled
        self.agent_vars = {
            source_id: self._make_agent_vars(source_id)
            for _label, source_id in SOURCE_CHOICES
        }
        self.agent_widgets: dict[str, dict] = {}
        self.tables: dict[str, ttk.Treeview] = {}
        self.limits_frames: dict[str, ttk.Frame] = {}
        self.limit_bar_canvases: dict[str, list[tuple[tk.Canvas, int | None]]] = {}
        self.status_var = tk.StringVar(value=backend_status_text("busy", "Loading data"))

        self._build_ui()
        self._bind_settings_persistence()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh(import_first=False)

    def _make_agent_vars(self, source: str) -> dict:
        visible_columns = setting_columns_for_source(self.settings, source)
        return {
            "limit": tk.IntVar(value=setting_int_for_source(
                self.settings,
                source,
                "limit",
                self.default_limit,
                1,
                50,
            )),
            "signal_enabled": tk.BooleanVar(value=setting_bool_for_source(
                self.settings,
                source,
                "signal_enabled",
                self.default_signal_enabled,
            )),
            "signal_threshold": tk.IntVar(value=setting_int_for_source(
                self.settings,
                source,
                "signal_threshold",
                self.default_signal_threshold,
                0,
                10000000,
            )),
            "signal_name": tk.StringVar(value=self._configured_signal_name(source)),
            "columns": {
                column_id: tk.BooleanVar(value=column_id in visible_columns)
                for column_id in TABLE_COLUMN_IDS
            },
            "visible_columns": visible_columns,
        }

    def active_vars(self) -> dict:
        return self.agent_vars[self.active_source]

    def _build_ui(self):
        self.root.title("Token Lens Mini")
        self._set_window_icon()
        self.root.minsize(760, 260)
        geometry = setting_str(self.settings, "geometry", "860x300")
        try:
            self.root.geometry(geometry)
        except tk.TclError:
            self.root.geometry("860x300")

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self.source_tabs = ttk.Notebook(outer)
        self.source_tab_ids = {}
        for label, value in SOURCE_CHOICES:
            tab = ttk.Frame(self.source_tabs, padding=(0, 8, 0, 0))
            self.source_tabs.add(tab, text=label)
            self.source_tab_ids[str(tab)] = value
            self._build_agent_tab(tab, value)
            if value == self.active_source:
                self.source_tabs.select(tab)
        self.source_tabs.pack(fill=tk.BOTH, expand=True)
        self.source_tabs.bind("<<NotebookTabChanged>>", self.switch_source)

    def _build_agent_tab(self, parent: ttk.Frame, source: str):
        vars_for_source = self.agent_vars[source]

        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(toolbar, text="Rows").pack(side=tk.LEFT)
        rows = ttk.Spinbox(
            toolbar,
            from_=1,
            to=50,
            width=4,
            textvariable=vars_for_source["limit"],
            command=lambda source_id=source: self.agent_refresh_or_save(source_id),
        )
        rows.pack(side=tk.LEFT, padx=(6, 10))
        rows.bind("<Return>", lambda _event, source_id=source: self.agent_refresh_or_save(source_id))
        rows.bind("<FocusOut>", lambda _event, source_id=source: self.agent_refresh_or_save(source_id))

        ttk.Button(toolbar, text="Refresh", command=lambda: self.refresh(import_first=True)).pack(side=tk.LEFT)
        columns_menu = tk.Menu(self.root, tearoff=False)
        for column in TABLE_COLUMNS:
            column_id = column["id"]
            columns_menu.add_checkbutton(
                label=column["label"],
                variable=vars_for_source["columns"][column_id],
                command=lambda source_id=source: self.apply_column_visibility(source_id),
            )
        ttk.Menubutton(toolbar, text="Columns", menu=columns_menu).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Checkbutton(toolbar, text="Signal", variable=vars_for_source["signal_enabled"]).pack(side=tk.LEFT, padx=(10, 4))
        ttk.Spinbox(
            toolbar,
            from_=0,
            to=10000000,
            increment=1000,
            width=8,
            textvariable=vars_for_source["signal_threshold"],
        ).pack(side=tk.LEFT, padx=(0, 4))
        signal_picker = ttk.Combobox(
            toolbar,
            width=11,
            state="readonly",
            values=tuple(SIGNAL_CHOICES.keys()),
            textvariable=vars_for_source["signal_name"],
        )
        signal_picker.pack(side=tk.LEFT)
        signal_picker.bind("<<ComboboxSelected>>", lambda _event, source_id=source: self.play_signal(source_id))
        ttk.Label(toolbar, textvariable=self.status_var, anchor=tk.E).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        limits_frame = ttk.Frame(parent)
        limits_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            limits_frame,
            text="Limits loading",
            anchor=tk.W,
        ).pack(fill=tk.X)
        self.limits_frames[source] = limits_frame
        self.limit_bar_canvases[source] = []

        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        table = ttk.Treeview(table_frame, columns=TABLE_COLUMN_IDS, show="headings", height=vars_for_source["limit"].get())
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=table.xview)
        table.configure(xscrollcommand=x_scroll.set)
        for column in TABLE_COLUMNS:
            column_id = column["id"]
            table.heading(column_id, text=column["label"])
            table.column(
                column_id,
                width=column["width"],
                minwidth=column["minwidth"],
                anchor=column["anchor"],
                stretch=column["stretch"],
            )
        self.tables[source] = table
        self.apply_column_visibility(source, save=False)
        table.tag_configure("over-limit", background="#fff1b8")
        table.pack(fill=tk.BOTH, expand=True)
        x_scroll.pack(fill=tk.X)
        self.agent_widgets[source] = {"columns_menu": columns_menu, "x_scroll": x_scroll}

    def _bind_settings_persistence(self):
        for source, vars_for_source in self.agent_vars.items():
            for variable in (
                vars_for_source["limit"],
                vars_for_source["signal_enabled"],
                vars_for_source["signal_threshold"],
                vars_for_source["signal_name"],
            ):
                variable.trace_add("write", lambda *_args, source_id=source: self.schedule_settings_save())
        self.root.bind("<Configure>", lambda _event: self.schedule_settings_save(), add="+")
        self.root.after_idle(self.enable_settings_save)

    def apply_column_visibility(self, source: str | None = None, save: bool = True):
        source = normalize_source(source or self.active_source)
        vars_for_source = self.agent_vars[source]
        selected = tuple(
            column_id
            for column_id in TABLE_COLUMN_IDS
            if vars_for_source["columns"][column_id].get()
        )
        if not selected:
            selected = ("task",)
            vars_for_source["columns"]["task"].set(True)
        vars_for_source["visible_columns"] = selected
        table = self.tables.get(source)
        if table is not None:
            table.configure(displaycolumns=selected)
        if save:
            self.schedule_settings_save()

    def enable_settings_save(self):
        self.settings_save_ready = True

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
        self.status_var.set(backend_status_text("busy", "Importing data" if import_first else "Loading data"))
        self._run_worker(lambda: self._refresh_worker(import_first))

    def schedule_settings_save(self):
        if self.closed or not self.settings_save_enabled or not self.settings_save_ready:
            return
        if self.settings_after_id is not None:
            self.root.after_cancel(self.settings_after_id)
        self.settings_after_id = self.root.after(400, self.save_settings_now)

    def save_settings_now(self, source: str | None = None):
        self.settings_after_id = None
        if not self.settings_save_enabled or not self.settings_save_ready:
            return
        source = normalize_source(source or self.active_source)
        agents = self.settings.get("agents")
        agents = dict(agents) if isinstance(agents, dict) else {}
        for _label, source_id in SOURCE_CHOICES:
            agents[source_id] = self.agent_settings_snapshot(source_id)
        active_snapshot = agents[source]
        snapshot = {
            **self.settings,
            "base_url": self.api.base_url,
            "limit": active_snapshot["limit"],
            "refresh_ms": self.refresh_ms,
            "range": self.range_key,
            "source": source,
            "signal_enabled": active_snapshot["signal_enabled"],
            "signal_threshold": active_snapshot["signal_threshold"],
            "signal": active_snapshot["signal"],
            "columns": list(active_snapshot["columns"]),
            "agents": agents,
            "geometry": self.root.geometry(),
        }
        try:
            save_mini_settings(snapshot)
            self.settings = snapshot
        except OSError:
            pass

    def agent_settings_snapshot(self, source_id: str) -> dict:
        vars_for_source = self.agent_vars[source_id]
        signal_name = vars_for_source["signal_name"].get()
        if signal_name not in SIGNAL_CHOICES:
            signal_name = self.default_signal_name
        return {
            "limit": self.read_int_var(vars_for_source["limit"], DEFAULT_LIMIT, 1, 50),
            "signal_enabled": self.read_bool_var(vars_for_source["signal_enabled"], True),
            "signal_threshold": self.read_int_var(
                vars_for_source["signal_threshold"],
                DEFAULT_SIGNAL_THRESHOLD,
                0,
                10000000,
            ),
            "signal": signal_name,
            "columns": list(vars_for_source["visible_columns"]),
        }

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
        signal_name = self.active_vars()["signal_name"].get()
        return signal_name if signal_name in SIGNAL_CHOICES else "Exclamation"

    def _configured_signal_name(self, source: str) -> str:
        signal_name = setting_str_for_source(self.settings, source, "signal", self.default_signal_name)
        return signal_name if signal_name in SIGNAL_CHOICES else self.default_signal_name

    def current_source(self) -> str:
        if not hasattr(self, "source_tabs"):
            return self.active_source
        selected = self.source_tabs.select()
        return normalize_source(self.source_tab_ids.get(selected, self.active_source))

    def switch_source(self, _event=None):
        source = self.current_source()
        if source == self.active_source:
            return
        self.active_source = source
        self.data_version = None
        self.seen_signal_rows = set()
        self.signal_seen_initialized = False
        self.last_signal_key = None
        self.schedule_settings_save()
        self.refresh(import_first=False)

    def agent_refresh_or_save(self, source: str):
        self.apply_column_visibility(source, save=False)
        if source == self.active_source:
            self.refresh(import_first=False)
            return
        self.schedule_settings_save()

    def _run_worker(self, target):
        self.worker_running = True
        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def _poll_worker(self):
        try:
            self.run_with_api_recovery(self.poll_once)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self._ui(lambda: self.set_error(error))
        finally:
            self._ui(self._finish_worker)

    def _refresh_worker(self, import_first: bool):
        try:
            self.run_with_api_recovery(lambda: self.refresh_once(import_first))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self._ui(lambda: self.set_error(error))
        finally:
            self._ui(self._finish_worker)

    def poll_once(self):
        state = self.api.get_json("/api/state")
        import_status = state.get("import_status") if isinstance(state, dict) else None
        source_warnings = state.get("source_warnings") if isinstance(state, dict) else None
        source_context = self.load_source_context()
        if self.data_version is None or state.get("version") != self.data_version:
            rows = self.load_rows()
            self._ui(lambda: self.render_rows(rows, state.get("version"), source_context, import_status, source_warnings))
        else:
            self._ui(lambda: self.render_source_context(source_context))
            self._ui(lambda: self.set_checked_status(import_status, source_warnings))

    def refresh_once(self, import_first: bool):
        if import_first:
            dashboard = self.api.post_json("/api/refresh", self.query())
            rows = dashboard.get("tasks", [])
            version = dashboard.get("state", {}).get("version")
            import_status = dashboard.get("import_status")
            source_warnings = dashboard.get("source_warnings")
            source_context = self.source_context_from_dashboard(dashboard)
        else:
            rows = self.load_rows()
            state = self.api.get_json("/api/state")
            version = state.get("version")
            import_status = state.get("import_status")
            source_warnings = state.get("source_warnings")
            source_context = self.load_source_context()
        self._ui(lambda: self.render_rows(rows, version, source_context, import_status, source_warnings))

    def run_with_api_recovery(self, operation):
        try:
            return operation()
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            if not self.try_recover_local_server(error):
                raise
            return operation()

    def try_recover_local_server(self, error: Exception) -> bool:
        if not is_local_api_url(self.api.base_url) or not is_connection_refused(error):
            return False
        now = time.monotonic()
        if now - self.last_server_start_attempt < SERVER_START_RETRY_SECONDS:
            LOGGER.warning("local server recovery skipped retry_window_seconds=%s error=%s", SERVER_START_RETRY_SECONDS, error)
            return False
        self.last_server_start_attempt = now
        self._ui(lambda: self.status_var.set(backend_status_text("busy", "Starting local server")))
        LOGGER.warning("local server connection refused; attempting recovery base_url=%s error=%s", self.api.base_url, error)
        try:
            start_local_server_process()
        except OSError:
            LOGGER.exception("local server recovery failed during process start")
            return False
        if not wait_for_api(self.api):
            LOGGER.error("local server recovery failed waiting for api base_url=%s", self.api.base_url)
            return False
        self._ui(lambda: self.status_var.set(backend_status_text("online", "Local server restarted")))
        LOGGER.info("local server recovery succeeded base_url=%s", self.api.base_url)
        return True

    def _finish_worker(self):
        self.worker_running = False
        self.schedule_poll()

    def _ui(self, callback):
        if not self.closed:
            self.root.after(0, callback)

    def query(self) -> dict:
        return {"limit": self.current_limit(), "range": self.range_key, "source": self.current_source()}

    def source_query(self) -> dict:
        return {"range": self.range_key, "source": self.current_source()}

    def load_rows(self) -> list[dict]:
        return self.api.get_json("/api/tasks", self.query())

    def load_summary(self) -> dict:
        payload = self.api.get_json("/api/summary", self.source_query())
        summary = payload.get("summary") if isinstance(payload, dict) else None
        return summary if isinstance(summary, dict) else {}

    def load_source_context(self) -> dict:
        source = self.current_source()
        if source == "opencode":
            return {"source": source, "summary": self.load_summary()}
        return {"source": source, "limits": self.load_usage_limits()}

    def source_context_from_dashboard(self, dashboard: dict) -> dict:
        source = self.current_source()
        if source == "opencode":
            summary_payload = dashboard.get("summary") if isinstance(dashboard, dict) else None
            summary = summary_payload.get("summary") if isinstance(summary_payload, dict) else None
            return {"source": source, "summary": summary if isinstance(summary, dict) else {}}
        limits = dashboard.get("usage_limits") if isinstance(dashboard, dict) else None
        return {"source": source, "limits": limits}

    def load_usage_limits(self) -> dict:
        try:
            return self.api.get_json("/api/usage-limits")
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            return {"ok": False, "error": str(error), "windows": []}

    def current_limit(self) -> int:
        limit_var = self.active_vars()["limit"]
        try:
            value = limit_var.get()
        except tk.TclError:
            value = DEFAULT_LIMIT
            limit_var.set(value)
        value = clamp(value, 1, 50)
        if limit_var.get() != value:
            limit_var.set(value)
        return value

    def render_source_context(self, context: dict | None):
        context = context if isinstance(context, dict) else {}
        if context.get("source") == "opencode":
            self.render_opencode_cost(context.get("summary"))
            return
        self.render_usage_limits(context.get("limits"))

    def clear_source_frame(self):
        limits_frame = self.limits_frames[self.active_source]
        for child in limits_frame.winfo_children():
            child.destroy()
        self.limit_bar_canvases[self.active_source] = []

    def render_opencode_cost(self, summary: dict | None):
        self.clear_source_frame()
        summary = summary if isinstance(summary, dict) else {}
        limits_frame = self.limits_frames[self.active_source]
        limits_frame.columnconfigure(0, weight=1)

        ttk.Label(
            limits_frame,
            text="OpenCode spend",
            font=("TkDefaultFont", 9, "bold"),
            anchor=tk.W,
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(
            limits_frame,
            text=f"Cost {format_cost(summary.get('estimated_cost'))}",
            anchor=tk.W,
        ).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Label(
            limits_frame,
            text=f"Tokens {format_number(summary.get('total_tokens'))}",
            anchor=tk.W,
        ).grid(row=0, column=2, sticky="w", padx=(0, 12))
        ttk.Label(
            limits_frame,
            text=f"Calls {format_number(summary.get('turns'))}",
            anchor=tk.W,
        ).grid(row=0, column=3, sticky="w")

    def render_usage_limits(self, snapshot: dict | None):
        self.clear_source_frame()

        groups = usage_limit_groups(snapshot)
        if not groups:
            ttk.Label(
                self.limits_frames[self.active_source],
                text=usage_limits_text(snapshot),
                anchor=tk.W,
            ).pack(fill=tk.X)
            return

        limits_frame = self.limits_frames[self.active_source]
        for column, group in enumerate(groups):
            limits_frame.columnconfigure(column, weight=1, uniform="limits")
            group_frame = ttk.Frame(limits_frame, padding=(0, 0, 12, 0))
            group_frame.grid(row=0, column=column, sticky="ew")
            group_frame.columnconfigure(0, weight=1)
            ttk.Label(
                group_frame,
                text=usage_limit_name(group),
                font=("TkDefaultFont", 9, "bold"),
                anchor=tk.W,
            ).grid(row=0, column=0, sticky="ew", pady=(0, 2))

            for row_index, row in enumerate(group.get("windows", []), start=1):
                self.add_limit_row(group_frame, row_index, row)
        self.root.after_idle(self.draw_limit_bars)

    def add_limit_row(self, parent: ttk.Frame, row_index: int, row: dict):
        remaining = limit_remaining_percent(row)
        reset = format_limit_reset(row.get("reset_at"))
        percent_text = "-" if remaining is None else f"{remaining}%"
        reset_text = f", reset {reset}" if reset else ""

        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row_index, column=0, sticky="ew", pady=(1, 2))
        row_frame.columnconfigure(0, weight=1)
        ttk.Label(
            row_frame,
            text=f"{limit_period(row)}: {percent_text} left{reset_text}",
            anchor=tk.W,
        ).grid(row=0, column=0, sticky="ew")
        canvas = tk.Canvas(
            row_frame,
            height=LIMIT_BAR_HEIGHT,
            highlightthickness=0,
            bg="#f0f0f0",
        )
        canvas.grid(row=1, column=0, sticky="ew", pady=(1, 0))
        canvas.bind("<Configure>", lambda _event: self.draw_limit_bars())
        self.limit_bar_canvases[self.active_source].append((canvas, remaining))

    def draw_limit_bars(self):
        canvases = [item for rows in self.limit_bar_canvases.values() for item in rows]
        for canvas, percent in canvases:
            try:
                width = max(1, canvas.winfo_width())
                height = max(1, canvas.winfo_height())
            except tk.TclError:
                continue
            canvas.delete("all")
            inner_left = 1
            inner_top = 1
            inner_right = width - 2
            inner_bottom = height - 2
            inner_width = max(1, inner_right - inner_left)
            canvas.create_rectangle(
                inner_left,
                inner_top,
                inner_right,
                inner_bottom,
                fill=LIMIT_BAR_TRACK_COLOR,
                outline=LIMIT_BAR_BORDER_COLOR,
                width=1,
            )
            canvas.create_line(
                inner_right,
                inner_top,
                inner_right,
                inner_bottom,
                fill=LIMIT_BAR_MARKER_COLOR,
                width=2,
            )
            if percent is None:
                continue
            fill_width = int(inner_width * percent / 100)
            fill_right = inner_left + max(1, fill_width)
            canvas.create_rectangle(
                inner_left,
                inner_top,
                min(fill_right, inner_right),
                inner_bottom,
                fill=limit_bar_fill_color(percent),
                width=0,
            )
            canvas.create_rectangle(
                inner_left,
                inner_top,
                inner_right,
                inner_bottom,
                outline=LIMIT_BAR_BORDER_COLOR,
                width=1,
            )
            canvas.create_line(
                inner_right,
                inner_top,
                inner_right,
                inner_bottom,
                fill=LIMIT_BAR_MARKER_COLOR,
                width=2,
            )
            if percent >= 100 and width >= 72:
                canvas.create_text(
                    inner_right - 20,
                    height // 2,
                    text="FULL",
                    anchor=tk.CENTER,
                    fill="#ffffff",
                    font=("TkDefaultFont", 7, "bold"),
                )

    def render_rows(
        self,
        rows: list[dict],
        version,
        source_context: dict | None = None,
        import_status: dict | None = None,
        source_warnings: list | None = None,
    ):
        self.data_version = version
        if source_context is not None:
            self.render_source_context(source_context)
        table = self.tables[self.active_source]
        table.configure(height=self.current_limit())
        threshold = self.current_signal_threshold()
        for item in table.get_children():
            table.delete(item)
        for row in rows[: self.current_limit()]:
            over_limit = (
                row.get("has_usage", 1) not in (0, False)
                and threshold > 0
                and parse_int(row.get("total_tokens_per_call")) > threshold
            )
            table.insert(
                "",
                tk.END,
                tags=("over-limit",) if over_limit else (),
                values=tuple(table_cell_value(column_id, row) for column_id in TABLE_COLUMN_IDS),
            )
        self.maybe_signal(rows, version, threshold)
        status_text = refresh_status_text(import_status, source_warnings)
        state = "busy" if isinstance(import_status, dict) and import_status.get("status") == "running" else "online"
        self.status_var.set(backend_status_text(state, status_text or f"Updated {time.strftime('%H:%M:%S')}"))

    def set_checked_status(self, import_status: dict | None = None, source_warnings: list | None = None):
        status_text = refresh_status_text(import_status, source_warnings)
        state = "busy" if isinstance(import_status, dict) and import_status.get("status") == "running" else "online"
        self.status_var.set(backend_status_text(state, status_text or f"Checked {time.strftime('%H:%M:%S')}"))

    def set_error(self, error: Exception):
        self.status_var.set(backend_status_text("offline", f"Error: {error}"))

    def current_signal_threshold(self) -> int:
        threshold_var = self.active_vars()["signal_threshold"]
        try:
            value = threshold_var.get()
        except tk.TclError:
            value = DEFAULT_SIGNAL_THRESHOLD
            threshold_var.set(value)
        value = max(0, value)
        if threshold_var.get() != value:
            threshold_var.set(value)
        return value

    def signal_row_key(self, row: dict) -> tuple:
        thread_id = row.get("thread_id")
        turn_id = row.get("turn_id")
        if thread_id and turn_id:
            return ("task", thread_id, turn_id)
        return (
            "fallback",
            row.get("finished_at"),
            row.get("models"),
            parse_int(row.get("model_calls")),
            parse_int(row.get("total_tokens")),
        )

    def maybe_signal(self, rows: list[dict], version, threshold: int):
        if threshold <= 0:
            self.seen_signal_rows.update(
                self.signal_row_key(row)
                for row in rows[: self.current_limit()]
            )
            self.signal_seen_initialized = True
            return

        visible_rows = rows[: self.current_limit()]
        visible_keys = {self.signal_row_key(row) for row in visible_rows}
        new_over_limit_keys = []
        for row in visible_rows:
            row_key = self.signal_row_key(row)
            if row_key in self.seen_signal_rows:
                continue
            if row.get("has_usage", 1) in (0, False):
                continue
            if parse_int(row.get("total_tokens_per_call")) > threshold:
                new_over_limit_keys.append(row_key)
        self.seen_signal_rows.update(visible_keys)

        if not self.signal_seen_initialized:
            self.signal_seen_initialized = True
            return
        if not self.active_vars()["signal_enabled"].get() or not new_over_limit_keys:
            return

        self.signal_seen_initialized = True
        signal_key = (
            version,
            threshold,
            self.active_vars()["signal_name"].get(),
            tuple(repr(key) for key in new_over_limit_keys),
        )
        if signal_key == self.last_signal_key:
            return
        self.last_signal_key = signal_key
        self.play_signal()

    def play_signal(self, source: str | None = None):
        source = normalize_source(source or self.active_source)
        signal_name = self.agent_vars[source]["signal_name"].get()
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
    settings, settings_save_enabled = load_mini_settings_with_status()
    configure_logging()
    base_url = setting_str(settings, "base_url", args.base_url)
    limit = setting_int(settings, "limit", args.limit, 1, 50)
    refresh_ms = setting_int(settings, "refresh_ms", args.refresh_ms, 1000, 60000)
    range_key = setting_str(settings, "range", args.range_key)
    source = normalize_source(setting_str(settings, "source", args.source))
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
    LOGGER.info("mini client starting base_url=%s refresh_ms=%s source=%s", base_url, refresh_ms, source)
    root = tk.Tk()
    app = MiniClientApp(
        root,
        ApiClient(base_url),
        limit,
        refresh_ms,
        range_key,
        source,
        signal_threshold,
        signal_name,
        signal_enabled,
        settings,
        settings_save_enabled,
    )
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
