from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SidebarState:
    mode: str
    scanner_id: str


@dataclass(frozen=True)
class ScannerMeta:
    scanner_id: str
    name: str
    description: str

