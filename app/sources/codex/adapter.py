from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.sources.codex.reader import iter_log_rows_after, iter_usage_log_rows, latest_log_id
from app.sources.codex.thread_names import load_thread_metadata, load_thread_names


@dataclass(frozen=True)
class CodexUsageSource:
    logs_db: str
    session_index: str

    def iter_rows(self) -> Iterable[Mapping]:
        return iter_usage_log_rows(self.logs_db)

    def load_thread_names(self) -> dict[str, str]:
        return load_thread_names(self.session_index)

    def load_thread_metadata(self) -> dict[str, dict]:
        return load_thread_metadata(self.session_index)

    def iter_rows_after(self, last_id: int = 0):
        return iter_log_rows_after(self.logs_db, last_id)

    def latest_log_id(self) -> int:
        return latest_log_id(self.logs_db)
