from __future__ import annotations

import pandas as pd

from src.models import ScannerMeta
from src.scanners.base import BaseScanner, results_frame, rsi


class TrendContinuationScanner(BaseScanner):
    meta = ScannerMeta(
        scanner_id="trend_continuation",
        name="EMA Trend Continuation",
        description="Ranks symbols with stacked EMAs, steady pullbacks, and renewed volume.",
    )

    def scan(self, universe: dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for symbol, frame in universe.items():
            if len(frame) < 220:
                continue
            data = frame.copy()
            data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
            data["ema_50"] = data["close"].ewm(span=50, adjust=False).mean()
            data["ema_200"] = data["close"].ewm(span=200, adjust=False).mean()
            data["rsi"] = rsi(data["close"])
            data["vol_ratio"] = data["volume"].rolling(5).mean() / data["volume"].rolling(20).mean()
            clean = data.dropna()
            if clean.empty:
                continue
            last = clean.iloc[-1]

            trend_score = int(
                sum(
                    [
                        last["close"] > last["ema_20"],
                        last["ema_20"] > last["ema_50"],
                        last["ema_50"] > last["ema_200"],
                    ]
                )
                / 3
                * 100
            )
            momentum_score = int(min(max((last["rsi"] - 50) / 25, 0), 1) * 100)
            volume_score = int(min(last["vol_ratio"] / 2.5, 1) * 100)
            final_score = round((trend_score * 0.45) + (momentum_score * 0.35) + (volume_score * 0.2))

            if final_score < 55:
                continue

            rows.append(
                {
                    "Symbol": symbol,
                    "LTP": round(float(last["close"]), 2),
                    "Final Score": final_score,
                    "Trend Score": trend_score,
                    "Squeeze Score": 0,
                    "Momentum Score": momentum_score,
                    "Min in Squeeze": 0,
                    "Vol Ratio": round(float(last["vol_ratio"]), 1),
                    "RSI (14)": round(float(last["rsi"]), 1),
                    "Status": "TREND",
                }
            )

        return results_frame(rows)
