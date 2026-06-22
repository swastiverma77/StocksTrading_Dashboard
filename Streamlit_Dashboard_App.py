import os
import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from breeze_connect import BreezeConnect

# --- CONFIGURATION ---
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

NIFTY50_SYMBOLS = ["RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "TCS"]

def base_squeeze_math(df):
    """Sync'd with advanced_backtest.py logic."""
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

def load_and_update_data(breeze_client, symbol):
    file_path = os.path.join(DATA_FOLDER, f"{symbol}_5min.csv")
    
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        df = df.sort_index()
    else:
        st.error(f"File not found: {file_path}")
        return pd.DataFrame()

    # Gap Update Logic
    if breeze_client:
        last_ts = df.index.max()
        now = datetime.now()
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
                    new_data['datetime'] = pd.to_datetime(new_data['datetime'], format='ISO8601')
                    new_data.set_index('datetime', inplace=True)
                    df = pd.concat([df, new_data]).drop_duplicates().sort_index()
                    df.to_csv(file_path)
            except Exception as e:
                st.sidebar.error(f"Update failed for {symbol}: {e}")
    return df

# UI Logic...
# (Ensure your UI calls the updated base_squeeze_math function)
