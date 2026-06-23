from __future__ import annotations

import pandas as pd
import streamlit as st


def metric_card(title: str, value: str, sub: str, change: str, color: str = "#2378ff") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-title">{title}</div>
          <span class="metric-value">{value}</span>
          <span class="metric-sub">{sub}</span>
          <span class="metric-up">{change}</span>
          <div class="spark" style="box-shadow: inset 0 -2px 0 {color};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results_table(results: pd.DataFrame) -> None:
    if results.empty:
        st.info("No candidates found for the current scanner and score threshold.")
        return

    display = results.copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="medium"),
            "LTP": st.column_config.NumberColumn("LTP", format="%.2f"),
            "Final Score": st.column_config.ProgressColumn("Final Score", min_value=0, max_value=100),
            "Trend Score": st.column_config.ProgressColumn("Trend Score", min_value=0, max_value=100),
            "Squeeze Score": st.column_config.ProgressColumn("Squeeze Score", min_value=0, max_value=100),
            "Momentum Score": st.column_config.ProgressColumn("Momentum Score", min_value=0, max_value=100),
            "Vol Ratio": st.column_config.NumberColumn("Vol Ratio", format="%.1fx"),
        },
    )

