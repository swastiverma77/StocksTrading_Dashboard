import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    """Calculates standard Wilder's RSI"""
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def strategy_pure_squeeze(df):
    """1. Pure Squeeze Scan: Identifies stocks in a mature contraction phase (Watchlist Builder)."""
    df.columns = df.columns.str.strip().str.lower()
    
    for col in ['close', 'high', 'low', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Trend Filter (Simplified for squeeze phase)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['trend_ok'] = (df['close'] > df['ema200']) & (df['ema20'] > df['ema50'])

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

    # Signal: Currently in a mature squeeze 
    df['signal'] = df['trend_ok'] & df['squeeze_duration_met']
    return df

def strategy_momentum_breakout(df):
    """2. Pure Momentum Breakout: High volume expansion & momentum, ignoring prior squeeze."""
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

    # Breakout Triggers
    df['vol_sma20'] = df['volume'].rolling(20).mean()
    df['vol_expansion'] = df['volume'] / df['vol_sma20'].shift(1)
    df['prev_5_high'] = df['high'].shift(1).rolling(5).max()
    
    df['is_breakout'] = (
        (df['close'] > df['vwap']) & 
        (df['ema15'] > df['ema30']) & 
        (df['rsi'] > 55) & 
        (df['vol_expansion'] > 2.0) & 
        (df['close'] > df['prev_5_high'])
    )

    # Signal: Breaking out with extreme momentum
    df['signal'] = df['trend_ok'] & df['is_breakout']
    return df

def strategy_combined_elite(df):
    """3. Elite Combined: The original Holy Grail combining Squeeze + Breakout."""
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

def strategy_ema_crossover(df):
    """Simple EMA 20/50 Crossover Strategy for demonstration."""
    df.columns = df.columns.str.strip().str.lower()
    
    for col in ['close', 'high', 'low', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # Golden Cross: EMA20 crosses above EMA50 (Shift checks the previous candle)
    df['signal'] = (df['ema20'] > df['ema50']) & (df['ema20'].shift(1) <= df['ema50'].shift(1))
    return df
