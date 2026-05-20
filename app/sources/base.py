from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol


class UsageSource(Protocol):
    def iter_rows(self) -> Iterable[Mapping]:
        """Yield raw source rows containing usage metadata."""

    def load_thread_names(self) -> dict[str, str]:
        """Return known thread display names keyed by thread id."""
