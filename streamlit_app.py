import streamlit as st
import pandas as pd
import os
import sys
import warnings
import pytz

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
IST = pytz.timezone('Asia/Kolkata')
DATA_FOLDER = "data/"

def load_and_clean_data(file_path):
    """Parses the specific 3-row header CSV format and converts time to IST."""
    # Load raw data skipping standard headers, as we have custom ones
    raw_df = pd.read_csv(file_path, header=None)
    
    # Extract data from row 4 onwards (index 3)
    # A=Price (unused/placeholder), B=Close, C=High, D=Low, E=Open, F=Volume
    df = raw_df.iloc[3:, [1, 2, 3, 4, 5]].copy()
    df.columns = ['close', 'high', 'low', 'open', 'volume']
    
    # Extract Datetime from Column A (A4 onwards)
    df['datetime'] = raw_df.iloc[3:, 0]
    
    # Convert types
    for col in ['close', 'high', 'low', 'open', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Handle Timezone Conversion
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_convert(IST)
    df.set_index('datetime', inplace=True)
    return df.sort_index()

# --- SIDEBAR: SCANNER SELECTION ---
st.sidebar.header("⚙️ Scanner Settings")
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
        available_files = [f.replace("_5min.csv", "") for f in os.listdir(DATA_FOLDER) if f.endswith("_5min.csv")]
        
        if available_files:
            selected_symbol = st.selectbox("Select Symbol", sorted(available_files))
            
            if st.button("Run Scanner on Local Data"):
                file_path = os.path.join(DATA_FOLDER, f"{selected_symbol}_5min.csv")
                try:
                    # Use our new cleaning function
                    df = load_and_clean_data(file_path)
                    
                    results = run_scanner(df)
                    st.session_state.results = results
                    st.success(f"Successfully processed {selected_symbol}!")
                except Exception as e:
                    st.error(f"Error parsing {selected_symbol}: {e}")
        else:
            st.warning("No '_5min.csv' files found in the 'data/' folder.")
    else:
        st.error(f"Data folder '{DATA_FOLDER}' not found.")

    if 'results' in st.session_state:
        st.dataframe(st.session_state.results)
