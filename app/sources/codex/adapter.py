from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.sources.codex.reader import iter_usage_log_rows
from app.sources.codex.thread_names import load_thread_names


@dataclass(frozen=True)
class CodexUsageSource:
    logs_db: str
    session_index: str

    def iter_rows(self) -> Iterable[Mapping]:
        return iter_usage_log_rows(self.logs_db)

    def load_thread_names(self) -> dict[str, str]:
        return load_thread_names(self.session_index)
