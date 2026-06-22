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

# Local storage for Streamlit Cloud (Ephemeral but works for the daily session)
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

# --- 1. STREAMLIT SESSION STATE CACHE ---
if "MEMORY_CACHE" not in st.session_state:
    st.session_state.MEMORY_CACHE = {}

# --- 2. DATA FETCHING ---
def fetch_icici_intraday(breeze_client, symbol, start_date, end_date):
    """Requests clean 5-minute OHLCV data directly from ICICI servers."""
    try:
        response = breeze_client.get_historical_data_v2(
            interval="5minute",
            from_date=start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            to_date=end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            stock_code=symbol,
            exchange_code="NSE",
            product_type="cash"
        )
        
        if response and response.get('status') == 200 and response.get('success'):
            df = pd.DataFrame(response['success'])
            if df.empty: return pd.DataFrame()
            
            df['datetime'] = pd.to_datetime(df['datetime'], format='ISO8601')
            df.set_index('datetime', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            return df.apply(pd.to_numeric, errors='coerce')
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- 3. ADVANCED INDICATOR ENGINES ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def base_squeeze_math(df):
    """Calculates core indicators used by both live and backtest scanners."""
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

    # Squeeze States
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

    # Core Signal logic
    df['signal'] = df['trend_ok'] & df['squeeze_duration_met'] & df['is_breakout']
    return df

def advanced_squeeze_live_scanner(df, symbol):
    """Scanner formatted for live real-time alerting."""
    if len(df) < 200: 
        return df, None

    df = base_squeeze_math(df)

    # --- REAL-TIME ALERT CHECK ---
    latest_row = df.iloc[-1]
    if latest_row['signal']:
        bbw_tier = "Exceptional" if df['bb_width'].iloc[-2] < 0.03 else ("Strong" if df['bb_width'].iloc[-2] < 0.04 else "Good")
        vol_tier = "Exceptional" if latest_row['vol_expansion'] > 5.0 else ("Strong" if latest_row['vol_expansion'] > 3.0 else "Good")
        
        signal_data = {
            "Symbol": symbol,
            "Time": df.index[-1].strftime('%H:%M'),
            "Close": f"₹{latest_row['close']:.2f}",
            "BBW_Tier": bbw_tier,
            "Vol_Spike": f"{latest_row['vol_expansion']:.1f}x",
            "RSI": f"{latest_row['rsi']:.1f}"
        }
        return df, signal_data
    
    return df, None

def advanced_squeeze_backtester(df, symbol):
    """Scanner formatted to track historical performance and 2-hour forward metrics."""
    if len(df) < 200: 
        return None

    df = base_squeeze_math(df)
    
    # Track the strength of the squeeze right before it broke out
    df['pre_breakout_bbw'] = df['bb_width'].shift(1)
    
    # Forward tracking (2 hours / 24 candles)
    df['max_high_2hr'] = df['high'].shift(-1).iloc[::-1].rolling(24, min_periods=1).max().iloc[::-1]
    df['max_gain_pct'] = ((df['max_high_2hr'] - df['close']) / df['close']) * 100

    signal_rows = df[df['signal'] == True].copy()
    if signal_rows.empty:
        return None

    signal_rows['Symbol'] = symbol
    signal_rows['BBW_Tier'] = np.where(signal_rows['pre_breakout_bbw'] < 0.03, 'Exceptional (<3%)',
                              np.where(signal_rows['pre_breakout_bbw'] < 0.04, 'Strong (<4%)', 'Good (<6%)'))
    signal_rows['Vol_Tier'] = np.where(signal_rows['vol_expansion'] > 5.0, 'Exceptional (>5.0x)',
                              np.where(signal_rows['vol_expansion'] > 3.0, 'Strong (>3.0x)', 'Good (>2.0x)'))
    signal_rows['RSI_Level'] = signal_rows['rsi'].round(1)
    signal_rows['Vol_Expansion_Ratio'] = signal_rows['vol_expansion'].round(2).astype(str) + 'x'
    signal_rows['Max_Gain_%'] = signal_rows['max_gain_pct'].round(2)
    signal_rows['Hit_1%'] = signal_rows['max_gain_pct'] >= 1.0
    signal_rows['Hit_2%'] = signal_rows['max_gain_pct'] >= 2.0

    return signal_rows[['Symbol', 'close', 'vwap', 'RSI_Level', 'BBW_Tier', 'Vol_Expansion_Ratio', 'Vol_Tier', 'Max_Gain_%', 'Hit_1%', 'Hit_2%']]

# --- 4. STREAMLIT UI & EXECUTION ENGINE ---
st.set_page_config(page_title="Institutional Scanner", layout="wide", page_icon="📈")

st.title("📈 Nifty 50 Institutional Squeeze Scanner")
st.markdown("Live 5-minute Intraday Breakout Dashboard & Backtester")

# --- SIDEBAR AUTHENTICATION ---
st.sidebar.header("🔑 Authentication")
st.sidebar.markdown("Enter your daily ICICI Session Token below.")

# Pull API Keys directly from Streamlit Secrets or Environment Variables
api_key = st.secrets.get("ICICI_API_KEY", os.environ.get("ICICI_API_KEY", ""))
secret_key = st.secrets.get("ICICI_SECRET_KEY", os.environ.get("ICICI_SECRET_KEY", ""))

if not api_key or not secret_key:
    st.sidebar.error("⚠️ API keys not found! Please configure `ICICI_API_KEY` and `ICICI_SECRET_KEY` in Streamlit Secrets.")

session_token = st.sidebar.text_input("Daily Session Token", type="password")

@st.cache_resource
def init_breeze(api, secret, token):
    try:
        client = BreezeConnect(api_key=api)
        client.generate_session(api_secret=secret, session_token=token)
        return client
    except Exception as e:
        return None

# --- MAIN DASHBOARD AREA ---
if st.sidebar.button("🔌 Connect to ICICI"):
    if not api_key or not secret_key:
        st.sidebar.error("❌ Missing API/Secret Keys in app configuration.")
    elif not session_token:
        st.sidebar.warning("⚠️ Please enter your Session Token.")
    else:
        breeze = init_breeze(api_key, secret_key, session_token)
        if breeze:
            st.sidebar.success("✅ Connected Successfully!")
        else:
            st.sidebar.error("❌ Connection Failed. Check your Session Token.")

breeze_client = init_breeze(api_key, secret_key, session_token) if (api_key and secret_key and session_token) else None

# Create interactive tabs
tab_live, tab_backtest = st.tabs(["🔴 Live Scanner", "⏪ Backtesting"])

# --- TAB 1: LIVE SCANNER ---
with tab_live:
    st.subheader("Real-Time Institutional Breakout Detection")
    st.markdown("Scans the absolute latest 5-minute candle for new valid squeeze setups.")
    
    if st.button("🚀 Run Live Market Scan", use_container_width=True, type="primary"):
        if not breeze_client:
            st.error("⚠️ Please connect to ICICI Direct in the sidebar first.")
        else:
            now = datetime.now()
            one_month_ago = now - timedelta(days=30)
            
            signals_found = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, symbol in enumerate(NIFTY50_SYMBOLS):
                status_text.text(f"Scanning {symbol} ({idx+1}/50)...")
                
                # A. LOAD FROM CACHE OR LOCAL CSV
                if symbol not in st.session_state.MEMORY_CACHE:
                    file_path = os.path.join(DATA_FOLDER, f"{symbol}_5min.csv")
                    if os.path.exists(file_path):
                        try:
                            df = pd.read_csv(file_path)
                            df.columns = df.columns.str.strip().str.lower()
                            date_col = next((c for c in ['datetime', 'date', 'time', 'timestamp', 'unnamed: 0'] if c in df.columns), None)
                            if date_col:
                                df.index = pd.to_datetime(df[date_col], format='mixed', errors='coerce')
                            df = df[df.index.notnull()].sort_index()
                            req_cols = ['open', 'high', 'low', 'close', 'volume']
                            for col in req_cols:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                            st.session_state.MEMORY_CACHE[symbol] = df.dropna(subset=req_cols)[req_cols]
                        except:
                            pass

                # B. DYNAMIC FETCH LOGIC
                cached_df = st.session_state.MEMORY_CACHE.get(symbol, pd.DataFrame())
                catchup_start = max(cached_df.index.max(), one_month_ago) if not cached_df.empty else one_month_ago

                # C. FETCH LIVE BARS
                live_df = fetch_icici_intraday(breeze_client, symbol, catchup_start, now)
                
                # D. MERGE, PRUNE, AND SCAN
                if not live_df.empty:
                    combined_df = pd.concat([cached_df, live_df])
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')].sort_index()
                    combined_df = combined_df[combined_df.index >= one_month_ago]
                    
                    # Save to memory & local storage
                    st.session_state.MEMORY_CACHE[symbol] = combined_df
                    combined_df[['open', 'high', 'low', 'close', 'volume']].to_csv(os.path.join(DATA_FOLDER, f"{symbol}_5min.csv"))
                    
                    # Execute Math Logic
                    processed_df, signal_data = advanced_squeeze_live_scanner(combined_df, symbol)
                    
                    if signal_data:
                        signals_found.append(signal_data)

                time.sleep(0.6) # Throttling for ICICI API Limits
                progress_bar.progress((idx + 1) / len(NIFTY50_SYMBOLS))
                
            status_text.text(f"✅ Scan complete at {now.strftime('%H:%M:%S')}")
            
            # E. ALERT MANAGEMENT UI
            if signals_found:
                st.success(f"🔥 {len(signals_found)} Elite Breakout(s) Detected!")
                st.balloons()
                
                # Display beautifully as a dataframe
                results_df = pd.DataFrame(signals_found)
                st.dataframe(results_df, use_container_width=True)
            else:
                st.info("No elite squeeze breakouts detected in this cycle.")

# --- TAB 2: BACKTESTING ---
with tab_backtest:
    st.subheader("Historical 30-Day Strategy Validation")
    st.markdown("Runs the advanced criteria over local offline data to find historical hit rates without needing an API call.")
    
    if st.button("🕵️‍♂️ Run Historical Backtest", use_container_width=True):
        all_historical_signals = []
        files_processed = 0
        
        progress_bar_bt = st.progress(0)
        status_text_bt = st.empty()

        for idx, symbol in enumerate(NIFTY50_SYMBOLS):
            status_text_bt.text(f"Backtesting {symbol} ({idx+1}/50)...")
            
            df = None
            # Check RAM first
            if symbol in st.session_state.MEMORY_CACHE:
                df = st.session_state.MEMORY_CACHE[symbol]
            else:
                # Load directly from storage
                file_path = os.path.join(DATA_FOLDER, f"{symbol}_5min.csv")
                if os.path.exists(file_path):
                    try:
                        df = pd.read_csv(file_path)
                        df.columns = df.columns.str.strip().str.lower()
                        date_col = next((c for c in ['datetime', 'date', 'time', 'timestamp', 'unnamed: 0'] if c in df.columns), None)
                        if date_col:
                            df.index = pd.to_datetime(df[date_col], format='mixed', errors='coerce')
                        df = df[df.index.notnull()].sort_index()
                        req_cols = ['open', 'high', 'low', 'close', 'volume']
                        for col in req_cols:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        df = df.dropna(subset=req_cols)[req_cols]
                        # Populate cache so we don't have to read it again
                        st.session_state.MEMORY_CACHE[symbol] = df
                    except:
                        pass
            
            if df is not None and not df.empty:
                files_processed += 1
                report_df = advanced_squeeze_backtester(df, symbol)
                if report_df is not None and not report_df.empty:
                    all_historical_signals.append(report_df)
            
            progress_bar_bt.progress((idx + 1) / len(NIFTY50_SYMBOLS))
            
        status_text_bt.text(f"✅ Backtest execution finished. Processed {files_processed} local files.")

        if all_historical_signals:
            master_report = pd.concat(all_historical_signals)
            master_report = master_report.sort_index()
            master_report['close'] = master_report['close'].round(2)
            master_report['vwap'] = master_report['vwap'].round(2)
            
            # Metrics
            total_signals = len(master_report)
            hit_1pct = master_report['Hit_1%'].sum()
            hit_2pct = master_report['Hit_2%'].sum()
            
            st.divider()
            st.markdown(f"### 🏆 Strategy Report (Total Triggers: {total_signals})")
            
            col1, col2 = st.columns(2)
            col1.metric("Hit 1% Target (2-Hr Forward)", f"{hit_1pct}", f"{(hit_1pct/total_signals)*100:.1f}% Win Rate")
            col2.metric("Hit 2% Target (2-Hr Forward)", f"{hit_2pct}", f"{(hit_2pct/total_signals)*100:.1f}% Win Rate")
            
            st.dataframe(master_report, use_container_width=True)
        else:
            if files_processed == 0:
                st.warning("⚠️ No local data found! Please run the Live Scanner at least once to download the 30-day baseline.")
            else:
                st.info("📉 Backtest completed, but no signals matched the advanced criteria across the history.")
