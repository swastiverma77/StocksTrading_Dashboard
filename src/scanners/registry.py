from __future__ import annotations

from src.models import ScannerMeta
from src.scanners.base import BaseScanner
from src.scanners.squeeze_momentum import SqueezeMomentumScanner
from src.scanners.trend_continuation import TrendContinuationScanner


_SCANNERS: dict[str, type[BaseScanner]] = {
    SqueezeMomentumScanner.meta.scanner_id: SqueezeMomentumScanner,
    TrendContinuationScanner.meta.scanner_id: TrendContinuationScanner,
}


def scanner_options() -> list[ScannerMeta]:
    return [scanner.meta for scanner in _SCANNERS.values()]


def get_scanner(scanner_id: str) -> BaseScanner:
    scanner_cls = _SCANNERS.get(scanner_id, SqueezeMomentumScanner)
    return scanner_cls()

