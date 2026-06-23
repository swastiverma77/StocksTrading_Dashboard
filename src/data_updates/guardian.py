from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import DATA_DIR, IST, NIFTY_50_SYMBOLS


OHLCV_COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]


class DataGuardian:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_universe(
        self,
        symbols: Iterable[str] = NIFTY_50_SYMBOLS,
        breeze_client: object | None = None,
        update_cache: bool = False,
    ) -> dict[str, pd.DataFrame]:
        universe: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            frame = self.load_and_update_symbol(
                symbol,
                breeze_client=breeze_client,
                update_cache=update_cache,
            )
            if not frame.empty:
                universe[symbol] = frame
        return universe

    def load_and_update_symbol(
        self,
        symbol: str,
        breeze_client: object | None = None,
        update_cache: bool = False,
    ) -> pd.DataFrame:
        path = self._path_for(symbol)
        if path.exists():
            cached = self._read_cache(path)
            start_at = cached["datetime"].max() + pd.Timedelta(minutes=5)
        else:
            if breeze_client is None:
                return pd.DataFrame(columns=OHLCV_COLUMNS)
            cached = pd.DataFrame(columns=OHLCV_COLUMNS)
            start_at = self._floor_5min(datetime.now(IST) - timedelta(days=30))

        if breeze_client is None or not update_cache:
            return cached

        end_at = self._floor_5min(datetime.now(IST))
        if start_at <= end_at:
            updates = self._fetch_updates(symbol, start_at, end_at, breeze_client)
            merged = pd.concat([cached, updates], ignore_index=True)
        else:
            merged = cached

        clean = self._normalize(merged)
        clean.to_csv(path, index=False)
        return clean

    def _path_for(self, symbol: str) -> Path:
        return self.data_dir / f"{symbol}_5min.csv"

    def _read_cache(self, path: Path) -> pd.DataFrame:
        raw = pd.read_csv(path)
        return self._normalize(raw)

    def _normalize(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        frame = frame.copy()
        frame.columns = [str(col).strip().lower() for col in frame.columns]
        rename_map = {
            "date": "datetime",
            "time": "datetime",
            "timestamp": "datetime",
            "datetime_ist": "datetime",
        }
        frame = frame.rename(columns=rename_map)
        frame = frame[[col for col in OHLCV_COLUMNS if col in frame.columns]]

        if "datetime" not in frame.columns:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        parsed = pd.to_datetime(frame["datetime"], errors="coerce", utc=True)
        frame["datetime"] = parsed.dt.tz_convert(IST)

        for col in ["open", "high", "low", "close", "volume"]:
            frame[col] = pd.to_numeric(frame.get(col), errors="coerce")

        frame = frame.dropna(subset=OHLCV_COLUMNS)
        frame = frame.drop_duplicates(subset=["datetime"]).sort_values("datetime")
        return frame[OHLCV_COLUMNS].reset_index(drop=True)

    def _fetch_updates(
        self,
        symbol: str,
        start_at: pd.Timestamp | datetime,
        end_at: pd.Timestamp | datetime,
        breeze_client: object | None,
    ) -> pd.DataFrame:
        if breeze_client is None:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        try:
            response = breeze_client.get_historical_data_v2(
                interval="5minute",
                from_date=pd.Timestamp(start_at).tz_convert("UTC").isoformat(),
                to_date=pd.Timestamp(end_at).tz_convert("UTC").isoformat(),
                stock_code=symbol,
                exchange_code="NSE",
                product_type="cash",
            )
            rows = response.get("Success", [])
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

    @staticmethod
    def _floor_5min(value: datetime) -> pd.Timestamp:
        return pd.Timestamp(value).floor("5min")
