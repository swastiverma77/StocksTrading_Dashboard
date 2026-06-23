from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from src.config import IST, NIFTY_50_SYMBOLS
from src.data_updates.guardian import DataGuardian
from src.scanners.base import BaseScanner
from src.session.breeze_session import BreezeSessionManager
from src.ui.components import metric_card, render_results_table


def render_dashboard(
    mode: str,
    scanner: BaseScanner,
    guardian: DataGuardian,
    session_manager: BreezeSessionManager,
) -> None:
    now = datetime.now(IST)
    header_left, header_right = st.columns([3, 1])
    with header_left:
        st.markdown("### Welcome back, Trader")
        st.markdown('<div class="miq-muted">Analyze. Scan. Trade. Win.</div>', unsafe_allow_html=True)
    with header_right:
        status = "LIVE" if session_manager.connected else "DEMO"
        st.markdown(
            f"""
            <div class="status-pill">
              <span>ICICI Breeze Connection</span>
              <span class="dot"></span>
              <strong>{status}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    mode_col, strategy_col, market_col = st.columns([2.1, 1.1, 1.1])
    with mode_col:
        st.markdown('<div class="miq-panel"><div class="miq-small-label">Mode Selection</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        cols[0].markdown(
            f'<div class="mode-card {"active" if mode == "Live Scan" else ""}"><b>Live Scan</b><br><span class="miq-muted">Scan real-time market</span></div>',
            unsafe_allow_html=True,
        )
        cols[1].markdown(
            f'<div class="mode-card {"active" if mode == "Backtesting" else ""}"><b>Backtesting</b><br><span class="miq-muted">Test strategy on historical data</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with strategy_col:
        st.markdown(
            f"""
            <div class="miq-panel">
              <div class="miq-small-label">Selected Strategy</div>
              <b>{scanner.meta.name}</b>
              <div class="miq-muted" style="margin-top:10px">{scanner.meta.description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with market_col:
        market_state = "OPEN" if _is_market_open(now) else "CLOSED"
        st.markdown(
            f"""
            <div class="miq-panel">
              <div class="miq-small-label">Market Status</div>
              <div>Market: <b style="color:#5df24d">{market_state}</b></div>
              <div>Time: {now.strftime("%I:%M:%S %p")}</div>
              <div>Date: {now.strftime("%d %b %Y")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    scan_button = st.button("Refresh Scan", use_container_width=False)
    if scan_button:
        with st.spinner("Updating local cache and scanning Nifty 50..."):
            universe = guardian.load_universe(
                symbols=NIFTY_50_SYMBOLS,
                breeze_client=session_manager.client if session_manager.connected else None,
                update_cache=session_manager.connected and mode == "Live Scan",
            )
            if not universe:
                st.warning("No usable stock CSV files were found in the data folder.")
            results = scanner.scan(universe)
            st.session_state["last_results"] = results
            st.session_state["last_updated"] = now

    results = st.session_state.get("last_results", pd.DataFrame())
    last_updated = st.session_state.get("last_updated", now)

    metric_cols = st.columns(5)
    with metric_cols[0]:
        metric_card("Active Momentum", str(_count_status(results, "MOMENTUM")), "Stocks", "+12%", "#2378ff")
    with metric_cols[1]:
        metric_card("Active Squeezes", str(int((results.get("Squeeze Score", pd.Series(dtype=int)) > 70).sum())), "Stocks", "+8%", "#b657ff")
    with metric_cols[2]:
        metric_card("Breakouts Today", str(_count_status(results, "BREAKOUT")), "Stocks", "+16%", "#ffbf2e")
    with metric_cols[3]:
        avg_score = int(results["Final Score"].mean()) if not results.empty else 0
        metric_card("Avg Final Score", str(avg_score), "/100", "+6", "#20c7ff")
    with metric_cols[4]:
        breadth = int((results["Final Score"].ge(60).mean() * 100)) if not results.empty else 0
        metric_card("Market Breadth", f"{breadth}%", "", "+9%", "#5df24d")

    st.write("")
    st.markdown(
        f"#### Top Trade Candidates  <span class='miq-muted' style='font-size:.9rem'>Last Updated: {last_updated.strftime('%I:%M:%S %p')}</span>",
        unsafe_allow_html=True,
    )
    render_results_table(results.head(20))

    st.write("")
    quick_cols = st.columns(4)
    quick_cols[0].container(border=True).write("Squeeze Watchlist\n\nHigh compression stocks")
    quick_cols[1].container(border=True).write("Emerging Momentum\n\nEarly momentum movers")
    quick_cols[2].container(border=True).write("Extended Stocks\n\nOverextended, be cautious")
    quick_cols[3].container(border=True).write("Score Movers\n\nBiggest score changes")


def _is_market_open(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def _count_status(results: pd.DataFrame, status: str) -> int:
    if results.empty or "Status" not in results:
        return 0
    return int(results["Status"].eq(status).sum())
