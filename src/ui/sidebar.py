from __future__ import annotations

import streamlit as st

from src.models import ScannerMeta, SidebarState
from src.session.breeze_session import BreezeSessionManager


def render_sidebar(
    scanner_options: list[ScannerMeta],
    default_scanner_id: str,
    session_manager: BreezeSessionManager,
) -> SidebarState:
    with st.sidebar:
        st.markdown(
            """
            <div class="miq-title">
              <div class="miq-logo">IQ</div>
              <div>
                <div>MOMENTUM <span style="color:#3a91ff">IQ</span></div>
                <div class="miq-muted">TRADING DASHBOARD</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        st.caption("NAVIGATION")
        mode = st.radio(
            "Mode",
            ["Live Scan", "Backtesting"],
            label_visibility="collapsed",
            index=0,
        )

        st.divider()
        st.caption("STRATEGY")
        scanner_names = {item.name: item.scanner_id for item in scanner_options}
        default_name = next(
            item.name for item in scanner_options if item.scanner_id == default_scanner_id
        )
        selected_name = st.selectbox(
            "Select Strategy",
            options=list(scanner_names.keys()),
            index=list(scanner_names.keys()).index(default_name),
        )

        with st.expander("Strategy Settings"):
            st.slider("Minimum Final Score", 0, 100, 60)
            st.slider("Lookback Candles", 100, 500, 220, step=20)

        st.divider()
        st.caption("ICICI BREEZE CONNECTION")
        token = st.text_input(
            "Session Token",
            value=session_manager.session_token,
            type="password",
        )
        if st.button("Initiate Connection", use_container_width=True):
            session_manager.connect(token)

        if session_manager.connected:
            st.success("Breeze session is live.")
        elif session_manager.error:
            st.warning(session_manager.error)
        else:
            st.info("Using existing CSV files in data/ until Breeze is connected.")

        with st.container(border=True):
            st.write("How to get Session Token?")
            st.caption("1. Login to ICICI Breeze Web")
            st.caption("2. Generate Session Token")
            st.caption("3. Paste above and connect")

    return SidebarState(mode=mode, scanner_id=scanner_names[selected_name])
