from __future__ import annotations

import pandas as pd

from src.models import ScannerMeta
from src.scanners.base import BaseScanner, results_frame, rsi, vwap


class SqueezeMomentumScanner(BaseScanner):
    meta = ScannerMeta(
        scanner_id="squeeze_momentum",
        name="Squeeze + Momentum",
        description="Compression breakout scanner using EMA trend, BB width, RSI, VWAP, and volume expansion.",
    )

    def scan(self, universe: dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for symbol, frame in universe.items():
            if len(frame) < 220:
                continue
            enriched = self._indicators(frame)
            if enriched.empty:
                continue
            last = enriched.iloc[-1]

            trend_score = self._trend_score(last)
            squeeze_score = self._squeeze_score(last)
            momentum_score = self._momentum_score(last)
            final_score = round((trend_score * 0.35) + (squeeze_score * 0.25) + (momentum_score * 0.4))

            if final_score < 60:
                continue

            rows.append(
                {
                    "Symbol": symbol,
                    "LTP": round(float(last["close"]), 2),
                    "Final Score": final_score,
                    "Trend Score": trend_score,
                    "Squeeze Score": squeeze_score,
                    "Momentum Score": momentum_score,
                    "Min in Squeeze": int(last["squeeze_minutes"]),
                    "Vol Ratio": round(float(last["vol_ratio"]), 1),
                    "RSI (14)": round(float(last["rsi"]), 1),
                    "Status": "BREAKOUT" if last["breakout"] else "MOMENTUM",
                }
            )

        return results_frame(rows)

    def _indicators(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        close = data["close"]
        for length in [15, 20, 30, 50, 200]:
            data[f"ema_{length}"] = close.ewm(span=length, adjust=False).mean()

        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper = mid + (2 * std)
        lower = mid - (2 * std)
        data["bb_width"] = (upper - lower) / mid
        data["bb_width_rank"] = data["bb_width"].rolling(100).rank(pct=True)
        data["vol_ratio"] = data["volume"].rolling(5).mean() / data["volume"].rolling(20).mean()
        data["rsi"] = rsi(close)
        data["vwap"] = vwap(data)
        data["range_pct"] = (data["high"] - data["low"]) / data["close"]
        data["range_rank"] = data["range_pct"].rolling(100).rank(pct=True)
        data["is_squeeze"] = (data["bb_width_rank"] <= 0.25) & (data["range_rank"] <= 0.35)
        data["squeeze_minutes"] = data["is_squeeze"].astype(int).groupby((~data["is_squeeze"]).cumsum()).cumsum() * 5
        data["breakout"] = (
            (data["close"] > data["vwap"])
            & (data["rsi"] > 55)
            & (data["vol_ratio"] > 2.0)
            & (data["close"] > data["ema_20"])
        )
        return data.dropna()

    @staticmethod
    def _trend_score(row: pd.Series) -> int:
        checks = [
            row["close"] > row["ema_15"],
            row["ema_15"] > row["ema_20"],
            row["ema_20"] > row["ema_30"],
            row["ema_30"] > row["ema_50"],
            row["close"] > row["ema_200"],
        ]
        return int(sum(checks) / len(checks) * 100)

    @staticmethod
    def _squeeze_score(row: pd.Series) -> int:
        compression = max(0, 1 - float(row["bb_width_rank"]))
        range_quality = max(0, 1 - float(row["range_rank"]))
        duration_bonus = min(float(row["squeeze_minutes"]) / 60, 1)
        return int(((compression * 0.45) + (range_quality * 0.35) + (duration_bonus * 0.2)) * 100)

    @staticmethod
    def _momentum_score(row: pd.Series) -> int:
        rsi_score = min(max((float(row["rsi"]) - 45) / 30, 0), 1)
        volume_score = min(float(row["vol_ratio"]) / 3, 1)
        vwap_score = 1 if row["close"] > row["vwap"] else 0
        return int(((rsi_score * 0.35) + (volume_score * 0.4) + (vwap_score * 0.25)) * 100)
