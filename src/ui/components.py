from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st


def metric_card(title: str, value: str, sub: str, change: str, color: str = "#2378ff") -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-title">{title}</div>'
        f'<span class="metric-value">{value}</span>'
        f'<span class="metric-sub">{sub}</span>'
        f'<span class="metric-up">{change}</span>'
        f'<div class="spark" style="box-shadow: inset 0 -2px 0 {color};"></div>'
        "</div>"
    )


def render_results_table(results: pd.DataFrame) -> None:
    if results.empty:
        st.info("No candidates found for the current scanner and score threshold.")
        return

    display = results.copy()
    display.insert(0, "Rank", range(1, len(display) + 1))

    columns = [
        "Rank",
        "Symbol",
        "LTP",
        "Final Score",
        "Trend Score",
        "Squeeze Score",
        "Momentum Score",
        "Vol Ratio",
        "RSI (14)",
        "Status",
    ]
    rows = "".join(_result_row(row, columns) for _, row in display[columns].iterrows())
    headers = "".join(f"<th>{escape(column)}</th>" for column in columns)
    st.markdown(
        f'<div class="results-table-wrap"><table class="results-table"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _result_row(row: pd.Series, columns: list[str]) -> str:
    cells = []
    for column in columns:
        value = row[column]
        if column == "Symbol":
            cells.append(f'<td class="symbol-cell">{escape(str(value))}</td>')
        elif column == "Status":
            cells.append(f'<td><span class="status-badge">{escape(str(value))}</span></td>')
        elif column in {"Final Score", "Trend Score", "Squeeze Score", "Momentum Score"}:
            score = int(value)
            cells.append(
                '<td>'
                f'<div class="score-cell"><span>{score}</span>'
                f'<div class="score-track"><div class="score-fill" style="width:{score}%"></div></div></div>'
                "</td>"
            )
        elif column == "Vol Ratio":
            cells.append(f"<td>{float(value):.1f}x</td>")
        elif column == "LTP":
            cells.append(f"<td>{float(value):.2f}</td>")
        elif column == "RSI (14)":
            cells.append(f"<td>{float(value):.1f}</td>")
        else:
            cells.append(f"<td>{escape(str(value))}</td>")
    return f"<tr>{''.join(cells)}</tr>"
