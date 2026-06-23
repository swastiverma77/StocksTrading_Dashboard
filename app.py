from __future__ import annotations

import streamlit as st

from src.config import APP_TITLE, DEFAULT_SCANNER_ID
from src.data_updates.guardian import DataGuardian
from src.scanners.registry import get_scanner, scanner_options
from src.session.breeze_session import BreezeSessionManager
from src.ui.dashboard import render_dashboard
from src.ui.sidebar import render_sidebar
from src.ui.theme import apply_theme


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="MIQ",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    session_manager = BreezeSessionManager.from_streamlit()
    guardian = DataGuardian()

    sidebar_state = render_sidebar(
        scanner_options=scanner_options(),
        default_scanner_id=DEFAULT_SCANNER_ID,
        session_manager=session_manager,
    )

    scanner = get_scanner(sidebar_state.scanner_id)
    render_dashboard(
        mode=sidebar_state.mode,
        scanner=scanner,
        guardian=guardian,
        session_manager=session_manager,
    )


if __name__ == "__main__":
    main()
