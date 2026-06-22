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

def calculate_rsi(series, period=14):
    """Calculates standard Wilder's RSI"""
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def base_squeeze_math(df):
    """Sync'd with advanced_backtest.py logic with added column normalization."""
    df.columns = df.columns.str.strip().str.lower()
    
    for col in ['close', 'high', 'low', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Trend Filter
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema30'] = df['close'].ewm(span=30, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['trend_ok'] = (df['close'] > df['ema200']) & (df['ema20'] > df['ema50']) & (df['ema50'] > df['ema200'])

    # Intraday VWAP
    df['date'] = df.index.date
    typical_price_vol = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
    df['vwap'] = typical_price_vol.groupby(df['date']).cumsum() / df['volume'].groupby(df['date']).cumsum()

    # RSI
    df['rsi'] = calculate_rsi(df['close'], period=14)

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_width'] = ((df['bb_mid'] + 2*df['bb_std']) - (df['bb_mid'] - 2*df['bb_std'])) / df['bb_mid']
    
    # Contraction Metrics
    df['vol_sma5'] = df['volume'].rolling(5).mean()
    df['vol_sma20'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['vol_sma5'] / df['vol_sma20']
    
    df['range'] = df['high'] - df['low']
    df['range_sma5'] = df['range'].rolling(5).mean()
    df['range_sma20'] = df['range'].rolling(20).mean()
    df['range_ratio'] = df['range_sma5'] / df['range_sma20']

    # Squeeze States (Duration check)
    df['is_squeezed'] = (df['bb_width'] < 0.06) & (df['vol_ratio'] < 0.80) & (df['range_ratio'] < 0.90)
    df['squeeze_duration_met'] = df['is_squeezed'].shift(1).rolling(6).sum() == 6

    # Breakout Triggers
    df['vol_expansion'] = df['volume'] / df['vol_sma20'].shift(1)
    df['prev_5_high'] = df['high'].shift(1).rolling(5).max()
    
    df['is_breakout'] = (
        (df['close'] > df['vwap']) & 
        (df['ema15'] > df['ema30']) & 
        (df['rsi'] > 55) & 
        (df['vol_expansion'] > 2.0) & 
        (df['close'] > df['prev_5_high'])
    )

    # Final Core Signal
    df['signal'] = df['trend_ok'] & df['squeeze_duration_met'] & df['is_breakout']
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
            raw_df = pd.read_csv(file_path)
            
            # Detect the 3-row header format (Where A2 = "Ticker")
            if len(raw_df) > 2 and 'ticker' in str(raw_df.iloc[0, 0]).lower():
                raw_df = raw_df.iloc[2:, :6].copy()
                raw_df.columns = ['datetime', 'close', 'high', 'low', 'open', 'volume']
            else:
                raw_df.columns = raw_df.columns.str.strip().str.lower()
                if 'unnamed: 0' in raw_df.columns:
                    raw_df.rename(columns={'unnamed: 0': 'datetime'}, inplace=True)
                if 'price' in raw_df.columns and 'datetime' not in raw_df.columns:
                    raw_df.rename(columns={'price': 'datetime'}, inplace=True)
            
            date_col = next((c for c in ['datetime', 'date', 'time', 'timestamp'] if c in raw_df.columns), None)
            
            if date_col:
                raw_df.index = pd.to_datetime(raw_df[date_col], format='mixed', errors='coerce')
                raw_df = raw_df.drop(columns=[date_col], errors='ignore')
            else:
                raw_df.index = pd.to_datetime(raw_df.iloc[:, 0], format='mixed', errors='coerce')
                        
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in raw_df.columns:
                    raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce')
                    
            df = raw_df[raw_df.index.notnull()].dropna(subset=['close']).sort_index()
            
            if not df.empty:
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
        now_ist = datetime.now(IST)
        
        if last_ts < (now_ist - timedelta(minutes=5)):
            try:
                # ICICI API explicitly expects UTC time for its ISO8601 strings
                last_ts_utc = last_ts.astimezone(pytz.utc)
                now_utc = now_ist.astimezone(pytz.utc)
                
                response = breeze_client.get_historical_data_v2(
                    interval="5minute",
                    from_date=last_ts_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    to_date=now_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    stock_code=symbol,
                    exchange_code="NSE",
                    product_type="cash"
                )
                if response and 'success' in response:
                    new_data = pd.DataFrame(response['success'])
                    new_data['datetime'] = pd.to_datetime(new_data['datetime'], format='ISO8601').dt.tz_localize('UTC').dt.tz_convert(IST)
                    new_data.set_index('datetime', inplace=True)
                    
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, symbol in enumerate(NIFTY50_SYMBOLS):
            status_text.text(f"Scanning {symbol} ({idx+1}/50)...")
            df = load_and_update_data(st.session_state.breeze_client, symbol)
            if not df.empty:
                df = base_squeeze_math(df)
                if df.iloc[-1]['signal']:
                    signals.append({
                        "Symbol": symbol, 
                        "Time (IST)": df.index[-1].strftime('%Y-%m-%d %H:%M'), 
                        "Close": df.iloc[-1]['close']
                    })
            progress_bar.progress((idx + 1) / len(NIFTY50_SYMBOLS))
            
        status_text.text("✅ Scan Complete")
        if signals: 
            st.success(f"🔥 {len(signals)} Breakout(s) Detected!")
            st.dataframe(pd.DataFrame(signals), use_container_width=True)
        else: 
            st.info("No live elite signals found at this moment.")

with tab_backtest:
    st.subheader("Historical Backtest")
    if st.button("🕵️‍♂️ Run Historical Backtest"):
        results = []
        progress_bar_bt = st.progress(0)
        
        for idx, symbol in enumerate(NIFTY50_SYMBOLS):
            df = load_and_update_data(None, symbol)
            if not df.empty:
                df = base_squeeze_math(df)
                for i in df[df['signal'] == True].index:
                    pos = df.index.get_loc(i)
                    outcome = check_1_2_target(df, pos)
                    results.append({
                        "Symbol": symbol,
                        "DateTime (IST)": i.strftime('%Y-%m-%d %H:%M'),
                        "Price": df.loc[i, 'close'],
                        "Outcome": outcome
                    })
            progress_bar_bt.progress((idx + 1) / len(NIFTY50_SYMBOLS))
            
        if results: 
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else: 
            st.info("No historical signals found.")
