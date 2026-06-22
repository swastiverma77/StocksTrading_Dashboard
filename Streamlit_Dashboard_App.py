import os
import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from breeze_connect import BreezeConnect

# --- ENVIRONMENT CONFIGURATION ---
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
DATA_FOLDER = "data/Nifty_Live_Framework"
os.makedirs(DATA_FOLDER, exist_ok=True)

NIFTY50_SYMBOLS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL",
    "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC",
    "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT",
    "LTIM", "M&M", "MARUTI", "NTPC", "NESTLEIND",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL",
    "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
]

if "MEMORY_CACHE" not in st.session_state:
    st.session_state.MEMORY_CACHE = {}

def load_local_data(symbol):
    """Loads existing CSV from local folder."""
    file_path = os.path.join(DATA_FOLDER, f"{symbol}_5min.csv")
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df.sort_index()
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def fetch_gap_data(breeze_client, symbol, last_timestamp):
    """Only fetches data from the last timestamp to now."""
    now = datetime.now()
    if last_timestamp >= now - timedelta(minutes=5): return pd.DataFrame()
    
    try:
        response = breeze_client.get_historical_data_v2(
            interval="5minute",
            from_date=last_timestamp.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            to_date=now.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            stock_code=symbol,
            exchange_code="NSE",
            product_type="cash"
        )
        if response and 'success' in response:
            df = pd.DataFrame(response['success'])
            df['datetime'] = pd.to_datetime(df['datetime'], format='ISO8601')
            df.set_index('datetime', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric, errors='coerce')
    except:
        pass
    return pd.DataFrame()

def base_squeeze_math(df):
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_width'] = (4 * df['bb_std']) / df['bb_mid']
    df['rsi'] = 100 - (100 / (1 + df['close'].diff().clip(lower=0).ewm(14).mean() / -df['close'].diff().clip(upper=0).ewm(14).mean()))
    df['is_squeezed'] = (df['bb_width'] < 0.06)
    df['signal'] = (df['close'] > df['ema200']) & (df['is_squeezed'].shift(1).rolling(6).sum() == 6)
    return df

st.set_page_config(page_title="Institutional Scanner", layout="wide")
st.title("📈 Nifty 50 Local-Cache Scanner")

# Sidebar Auth
api_key = st.secrets.get("ICICI_API_KEY", os.environ.get("ICICI_API_KEY", ""))
secret_key = st.secrets.get("ICICI_SECRET_KEY", os.environ.get("ICICI_SECRET_KEY", ""))
session_token = st.sidebar.text_input("Session Token", type="password")
breeze_client = BreezeConnect(api_key=api_key) if api_key else None
if session_token and breeze_client: breeze_client.generate_session(api_secret=secret_key, session_token=session_token)

# Heartbeat
if breeze_client:
    st.sidebar.caption(f"Last heartbeat: {datetime.now().strftime('%H:%M:%S')}")

if st.button("🚀 Run Scan (Local + Gap Update)"):
    signals = []
    for symbol in NIFTY50_SYMBOLS:
        df = load_local_data(symbol)
        if not df.empty:
            gap_df = fetch_gap_data(breeze_client, symbol, df.index.max())
            if not gap_df.empty:
                df = pd.concat([df, gap_df]).drop_duplicates()
                df.to_csv(os.path.join(DATA_FOLDER, f"{symbol}_5min.csv"))
        
        if not df.empty:
            df = base_squeeze_math(df)
            if df.iloc[-1]['signal']:
                signals.append({"Symbol": symbol, "Close": df.iloc[-1]['close']})
        time.sleep(0.6) # Gentle sleep to prevent rate limits
    
    if signals: st.dataframe(pd.DataFrame(signals))
    else: st.info("No signals found.")
