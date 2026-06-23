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
        if path is not None and path.exists():
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
        output_path = path or self.data_dir / f"{symbol}_5min.csv"
        clean.to_csv(output_path, index=False)
        return clean

    def _path_for(self, symbol: str) -> Path | None:
        candidates = [
            self.data_dir / f"{symbol}_5min.csv",
            self.data_dir / f"{symbol}.csv",
            self.data_dir / f"{symbol}.NS.csv",
            self.data_dir / f"{symbol.lower()}_5min.csv",
            self.data_dir / f"{symbol.lower()}.csv",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        matches = sorted(self.data_dir.glob(f"{symbol}*.csv"))
        if matches:
            return matches[0]
        matches = sorted(self.data_dir.glob(f"{symbol.lower()}*.csv"))
        return matches[0] if matches else None

    def _read_cache(self, path: Path) -> pd.DataFrame:
        raw = pd.read_csv(path)
        clean = self._normalize(raw)
        if clean.empty:
            raw_no_header = pd.read_csv(path, header=None)
            clean = self._normalize_yfinance_multirow(raw_no_header)
        return clean

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

    def _normalize_yfinance_multirow(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty or len(frame) < 4:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        first_cell = str(frame.iloc[0, 0]).strip().lower()
        third_cell = str(frame.iloc[2, 0]).strip().lower()
        if first_cell != "price" or third_cell != "datetime":
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        columns = ["datetime"]
        columns.extend(str(value).strip().lower() for value in frame.iloc[0, 1:])
        data = frame.iloc[3:].copy()
        data = data.iloc[:, : len(columns)]
        data.columns = columns
        return self._normalize(data)

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
