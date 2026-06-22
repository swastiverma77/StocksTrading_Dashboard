import streamlit as st
import pandas as pd
import os
import sys
import warnings

# --- FIX: Ensure the project root is in the path ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the segregated strategies from the renamed folder
from Scanner_Strategies.Momentum_Squeeze import (
    strategy_pure_squeeze,
    strategy_momentum_breakout,
    strategy_combined_elite,
    strategy_ema_crossover
)

# --- CONFIGURATION ---
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
st.set_page_config(page_title="Trading Scanner Dashboard", layout="wide")

# Pointing to the data folder in your GitHub root
DATA_FOLDER = "data/"

# --- SIDEBAR: SCANNER SELECTION ---
st.sidebar.header("⚙️ Scanner Settings")

# Mapping UI labels to the imported functions
strategy_map = {
    "Pure Squeeze Scan": strategy_pure_squeeze,
    "Momentum Breakout": strategy_momentum_breakout,
    "Elite Combined": strategy_combined_elite,
    "EMA 20/50 Crossover": strategy_ema_crossover
}

selected_scanner = st.sidebar.selectbox("Select Scanner Logic", list(strategy_map.keys()))
run_scanner = strategy_map[selected_scanner]

# --- MAIN UI ---
st.title(f"📊 Trading Dashboard: {selected_scanner}")

tab_live, tab_backtest = st.tabs(["🔴 Live Scanner View", "⏪ Backtesting Data"])

with tab_backtest:
    st.header("Backtesting Data Loader")
    
    if os.path.exists(DATA_FOLDER):
        # Scan folder for files
        available_files = [f.replace("_5min.csv", "") for f in os.listdir(DATA_FOLDER) if f.endswith("_5min.csv")]
        
        if available_files:
            selected_symbol = st.selectbox("Select Symbol", sorted(available_files))
            
            if st.button("Run Scanner on Local Data"):
                file_path = os.path.join(DATA_FOLDER, f"{selected_symbol}_5min.csv")
                try:
                    df = pd.read_csv(file_path)
                    df.columns = df.columns.str.strip().str.lower()
                    
                    results = run_scanner(df)
                    st.session_state.results = results
                    st.success(f"Successfully processed {selected_symbol}!")
                except Exception as e:
                    st.error(f"Error reading {selected_symbol}: {e}")
        else:
            st.warning("No '_5min.csv' files found in the 'data/' folder.")
    else:
        st.error(f"Data folder '{DATA_FOLDER}' not found.")

    if 'results' in st.session_state:
        st.dataframe(st.session_state.results)

with tab_live:
    st.info("The Live Scanner is running in the background via live_scanner_cell4.py.")
    if os.path.exists(DATA_FOLDER):
        files = [os.path.join(DATA_FOLDER, f) for f in os.listdir(DATA_FOLDER) if f.endswith("_5min.csv")]
        if files:
            latest_file = max(files, key=os.path.getmtime)
            st.write(f"Latest Market Data Sync: {os.path.basename(latest_file)}")
