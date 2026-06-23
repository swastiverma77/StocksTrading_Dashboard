from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #050b14;
            --panel: #0b1422;
            --panel-soft: #111d2c;
            --line: #1b2b3f;
            --text: #f6f8fb;
            --muted: #9fb0c6;
            --blue: #2378ff;
            --cyan: #20c7ff;
            --green: #5df24d;
            --purple: #b657ff;
            --yellow: #ffbf2e;
        }
        html, body, .stApp { max-width: 100%; overflow-x: hidden; }
        .stApp { background: radial-gradient(circle at 50% 0%, #0a1424 0, #050b14 38%, #03070d 100%); color: var(--text); }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #091422 0%, #07111d 100%); border-right: 1px solid var(--line); }
        section[data-testid="stSidebar"] * { color: var(--text); }
        .block-container { padding-top: 1.9rem; max-width: 1380px; overflow-x: hidden; }
        div[data-testid="stHorizontalBlock"] { max-width: 100%; }
        .miq-title { display:flex; gap:12px; align-items:center; font-weight:800; font-size:1.25rem; letter-spacing:.02em; }
        .miq-logo { width:42px; height:42px; border-radius:12px; display:grid; place-items:center; background:linear-gradient(135deg,#123dff,#16b8ff); font-weight:900; }
        .miq-muted { color: var(--muted); font-size:.92rem; }
        .miq-panel { background: linear-gradient(180deg, rgba(17,29,44,.92), rgba(8,17,29,.92)); border: 1px solid var(--line); border-radius: 8px; padding: 18px; box-shadow: 0 16px 40px rgba(0,0,0,.26); }
        .miq-small-label { color: var(--muted); text-transform: uppercase; font-size:.78rem; letter-spacing:.06em; margin-bottom:10px; }
        .mode-card { border: 1px solid var(--line); border-radius:8px; padding:16px; min-height:94px; background:#0e1a2a; }
        .mode-card.active { border-color: var(--blue); background:linear-gradient(135deg, rgba(28,100,242,.34), rgba(14,26,42,.95)); }
        .metric-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:18px; width:100%; }
        .metric-card { background:linear-gradient(180deg,#0e1a2a,#091422); border:1px solid var(--line); border-radius:8px; padding:18px; min-height:136px; min-width:0; }
        .metric-title { font-size:.92rem; color:var(--text); margin-bottom:8px; }
        .metric-value { font-size:2rem; font-weight:800; line-height:1; }
        .metric-sub { color:var(--muted); font-size:.9rem; }
        .metric-up { color:var(--green); font-size:.85rem; float:right; margin-top:10px; }
        .spark { height:32px; margin-top:14px; border-radius:6px; background:linear-gradient(90deg, rgba(35,120,255,.12), rgba(93,242,77,.08)); }
        .status-pill { display:inline-flex; align-items:center; gap:8px; padding:9px 14px; border-radius:8px; border:1px solid var(--line); background:#0e1a2a; max-width:100%; white-space:normal; }
        .dot { width:10px; height:10px; background:var(--green); border-radius:50%; box-shadow:0 0 16px rgba(93,242,77,.7); }
        .stButton > button { background:linear-gradient(135deg,#1766e8,#0d4fb8); color:white; border:1px solid #2878ff; border-radius:8px; height:42px; }
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input { background:#091422; border:1px solid var(--line); color:var(--text); border-radius:8px; }
        div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; overflow:auto; max-width:100%; }
        .stDataFrame { max-width:100%; overflow:auto; }
        @media (max-width: 900px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .metric-grid { grid-template-columns: 1fr; gap:12px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
