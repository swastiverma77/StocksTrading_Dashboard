import os
import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
import streamlit as st
from breeze_connect import BreezeConnect

# --- CONFIGURATION ---
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
DATA_FOLDER = "data/"
os.makedirs(DATA_FOLDER, exist_ok=True)
IST = pytz.timezone('Asia/Kolkata')

NIFTY50_SYMBOLS = ["RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "TCS"]

def base_squeeze_math(df):
    """Sync'd with advanced_backtest.py logic with added column normalization."""
    # Normalize column names to lowercase to prevent KeyErrors
    df.columns = df.columns.str.strip().str.lower()
    
    # Ensure necessary columns are numeric
    for col in ['close', 'high', 'low', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # Bollinger Band Width
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_width'] = ((df['bb_mid'] + 2*df['bb_std']) - (df['bb_mid'] - 2*df['bb_std'])) / df['bb_mid']
    
    # Squeeze duration: 6 consecutive candles (30 mins) with BBW < 0.06
    df['is_squeezed'] = (df['bb_width'] < 0.06)
    df['squeeze_duration_met'] = df['is_squeezed'].shift(1).rolling(6).sum() == 6
    
    # Trend Filter
    df['trend_ok'] = (df['close'] > df['ema200']) & (df['ema20'] > df['ema50'])
    
    # Final Signal
    df['signal'] = df['trend_ok'] & df['squeeze_duration_met']
    return df

def check_1_2_target(df, signal_idx):
    """
    Checks if price hits +2% gain before -1% loss.
    Looks ahead for up to 24 bars (2 hours).
    """
    signal_price = df.iloc[signal_idx]['close']
    target_up = signal_price * 1.02
    target_down = signal_price * 0.99
    
    future_data = df.iloc[signal_idx+1 : signal_idx+25]
    
    for _, row in future_data.iterrows():
        if row['high'] >= target_up:
            return "✅ Hit 2% Target"
        if row['low'] <= target_down:
            return "❌ Stop Loss Hit"
    return "⏳ Still Open / No Target"

def load_and_update_data(breeze_client, symbol):
    file_path = os.path.join(DATA_FOLDER, f"{symbol}_5min.csv")
    df = pd.DataFrame()
    
    if os.path.exists(file_path):
        try:
            # Smart CSV reading to handle complex multi-row headers
            raw_df = pd.read_csv(file_path)
            
            # Detect the 3-row header format (Where A2 = "Ticker")
            if len(raw_df) > 2 and 'ticker' in str(raw_df.iloc[0, 0]).lower():
                # Drop the 'Ticker' and 'Datetime' heading rows (Index 0 and 1)
                # Keep only the first 6 columns to avoid trailing commas
                raw_df = raw_df.iloc[2:, :6].copy()
                # Map exactly to your specified layout: A:Datetime, B:Close, C:High, D:Low, E:Open, F:Volume
                raw_df.columns = ['datetime', 'close', 'high', 'low', 'open', 'volume']
            else:
                # Handle normal/standard format (used after the app updates the CSV)
                raw_df.columns = raw_df.columns.str.strip().str.lower()
                if 'unnamed: 0' in raw_df.columns:
                    raw_df.rename(columns={'unnamed: 0': 'datetime'}, inplace=True)
                if 'price' in raw_df.columns and 'datetime' not in raw_df.columns:
                    raw_df.rename(columns={'price': 'datetime'}, inplace=True)
            
            # Locate the datetime column dynamically
            date_col = next((c for c in ['datetime', 'date', 'time', 'timestamp'] if c in raw_df.columns), None)
            
            if date_col:
                raw_df.index = pd.to_datetime(raw_df[date_col], format='mixed', errors='coerce')
                raw_df = raw_df.drop(columns=[date_col], errors='ignore')
            else:
                raw_df.index = pd.to_datetime(raw_df.iloc[:, 0], format='mixed', errors='coerce')
                        
            # Ensure columns are truly numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in raw_df.columns:
                    raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce')
                    
            # Remove unparseable rows and sort
            df = raw_df[raw_df.index.notnull()].dropna(subset=['close']).sort_index()
            
            if not df.empty:
                # The strings have +00:00, so pandas knows it is UTC. We just convert to IST.
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC').tz_convert(IST)
                else:
                    df.index = df.index.tz_convert(IST)
                    
        except Exception as e:
            st.error(f"Error parsing local data for {symbol}: {e}")
            return pd.DataFrame()
    else:
        st.error(f"File not found: {file_path}")
        return pd.DataFrame()

    # Gap Update Logic
    if breeze_client and not df.empty:
        last_ts = df.index.max()
        now = datetime.now(IST)
        if last_ts < (now - timedelta(minutes=5)):
            try:
                response = breeze_client.get_historical_data_v2(
                    interval="5minute",
                    from_date=last_ts.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    to_date=now.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    stock_code=symbol,
                    exchange_code="NSE",
                    product_type="cash"
                )
                if response and 'success' in response:
                    new_data = pd.DataFrame(response['success'])
                    new_data['datetime'] = pd.to_datetime(new_data['datetime'], format='ISO8601').dt.tz_localize('UTC').dt.tz_convert(IST)
                    new_data.set_index('datetime', inplace=True)
                    
                    # Merge and deduplicate
                    df = pd.concat([df, new_data]).drop_duplicates().sort_index()
                    df.to_csv(file_path)
            except Exception as e:
                st.sidebar.error(f"Update failed for {symbol}: {e}")
    return df

# --- UI LAYOUT ---
st.set_page_config(page_title="Institutional Scanner", layout="wide")
st.title("📈 Nifty 50 Local-Cache Scanner (IST Time)")

if 'breeze_client' not in st.session_state:
    st.session_state.breeze_client = None

# Sidebar
st.sidebar.header("🔑 Authentication")
api_key = st.secrets.get("ICICI_API_KEY", os.environ.get("ICICI_API_KEY", ""))
secret_key = st.secrets.get("ICICI_SECRET_KEY", os.environ.get("ICICI_SECRET_KEY", ""))
session_token = st.sidebar.text_input("Session Token", type="password")

if st.sidebar.button("🔌 Connect to ICICI"):
    try:
        client = BreezeConnect(api_key=api_key)
        client.generate_session(api_secret=secret_key, session_token=session_token)
        st.session_state.breeze_client = client
        st.sidebar.success("Session Established!")
    except Exception as e:
        st.sidebar.error(f"Connection failed: {e}")

# Main Content
tab_live, tab_backtest = st.tabs(["🔴 Live Scanner", "⏪ Backtesting"])

with tab_live:
    if st.button("🚀 Run Scan & Update Data"):
        signals = []
        for symbol in NIFTY50_SYMBOLS:
            df = load_and_update_data(st.session_state.breeze_client, symbol)
            if not df.empty:
                df = base_squeeze_math(df)
                if df.iloc[-1]['signal']:
                    # Display localized time
                    signals.append({"Symbol": symbol, "Time (IST)": df.index[-1].strftime('%Y-%m-%d %H:%M'), "Close": df.iloc[-1]['close']})
        if signals: st.dataframe(pd.DataFrame(signals))
        else: st.info("No signals found.")

with tab_backtest:
    st.subheader("Historical Backtest")
    if st.button("🕵️‍♂️ Run Historical Backtest"):
        results = []
        for symbol in NIFTY50_SYMBOLS:
            df = load_and_update_data(None, symbol)
            if not df.empty:
                df = base_squeeze_math(df)
                for idx in df[df['signal'] == True].index:
                    pos = df.index.get_loc(idx)
                    outcome = check_1_2_target(df, pos)
                    results.append({
                        "Symbol": symbol,
                        "DateTime (IST)": idx.strftime('%Y-%m-%d %H:%M'),
                        "Price": df.loc[idx, 'close'],
                        "Outcome": outcome
                    })
        if results: st.dataframe(pd.DataFrame(results))
        else: st.info("No signals found.")
