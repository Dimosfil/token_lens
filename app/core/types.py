from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImportStats:
    scanned: int = 0
    imported: int = 0
    skipped: int = 0
    archived: int = 0
