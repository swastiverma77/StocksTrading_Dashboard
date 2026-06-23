from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from src.models import ScannerMeta


RESULT_COLUMNS = [
    "Symbol",
    "LTP",
    "Final Score",
    "Trend Score",
    "Squeeze Score",
    "Momentum Score",
    "Min in Squeeze",
    "Vol Ratio",
    "RSI (14)",
    "Status",
]


class BaseScanner(ABC):
    meta: ScannerMeta

    @abstractmethod
    def scan(self, universe: dict[str, pd.DataFrame]) -> pd.DataFrame:
        raise NotImplementedError


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def vwap(frame: pd.DataFrame) -> pd.Series:
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3
    return (typical * frame["volume"]).cumsum() / frame["volume"].cumsum()


def results_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values("Final Score", ascending=False).reset_index(drop=True)
