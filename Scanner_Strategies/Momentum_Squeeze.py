import pandas as pd
import numpy as np

def run_ranking_engine(df):
    """
    Core Ranking Engine logic as per requirements.
    Expects OHLCV data with Datetime index.
    """
    # 1. Indicators
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema30'] = df['close'].ewm(span=30, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['rsi'] = 100 - (100 / (1 + (df['close'].diff().clip(lower=0).ewm(alpha=1/14).mean() / 
                                  -df['close'].diff().clip(upper=0).ewm(alpha=1/14).mean())))
    
    df['date'] = df.index.date
    df['vwap'] = (((df['high'] + df['low'] + df['close']) / 3) * df['volume']).groupby(df['date']).cumsum() / \
                 df['volume'].groupby(df['date']).cumsum()
    
    df['bb_mid'] = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + (2 * std)
    df['bb_lower'] = df['bb_mid'] - (2 * std)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    
    df['v_sma5'] = df['volume'].rolling(5).mean()
    df['v_sma20'] = df['volume'].rolling(20).mean()
    df['range'] = df['high'] - df['low']
    df['r_sma5'] = df['range'].rolling(5).mean()
    df['r_sma20'] = df['range'].rolling(20).mean()
    
    # 2. Trend Score
    ema_score = (20 if df['ema20'].iloc[-1] > df['ema50'].iloc[-1] else 0) + \
                (10 if df['ema20'].iloc[-1] > df['ema20'].shift(5).iloc[-1] else 0) + \
                (10 if df['ema50'].iloc[-1] > df['ema50'].shift(5).iloc[-1] else 0)
    
    bullish_struct = (df['high'].diff() > 0) & (df['low'].diff() > 0)
    struct_ratio = bullish_struct.tail(20).sum() / 20
    struct_score = 30 if struct_ratio >= 0.8 else (20 if struct_ratio >= 0.6 else (10 if struct_ratio >= 0.4 else 0))
    
    h50 = df['high'].rolling(50).max().iloc[-1]
    l50 = df['low'].rolling(50).min().iloc[-1]
    pos_ratio = (df['close'].iloc[-1] - l50) / (h50 - l50) if (h50 - l50) != 0 else 0
    pos_score = 20 if pos_ratio >= 0.8 else (10 if pos_ratio >= 0.6 else 0)
    
    vwap_score = (5 if df['close'].iloc[-1] > df['vwap'].iloc[-1] else 0) + \
                 (5 if df['vwap'].iloc[-1] > df['vwap'].shift(5).iloc[-1] else 0)
    
    trend_score = min(100, ema_score + struct_score + pos_score + vwap_score)
    
    # 3. Squeeze Score
    is_sq = (df['bb_width'] <= (df['bb_width'].rolling(20).min() * 1.10)) & (df['v_sma5'] < df['v_sma20']) & (df['r_sma5'] < df['r_sma20'])
    sq_count = 0
    for i in range(len(is_sq)-1, -1, -1):
        if is_sq.iloc[i]: sq_count += 1
        else: break
    
    comp_ratio = df['bb_width'].rolling(20).min().iloc[-1] / df['bb_width'].iloc[-1]
    squeeze_score = min(100, (comp_ratio * 30) + ((df['v_sma5'].iloc[-1]/df['v_sma20'].iloc[-1]) * 20) + 
                        ((df['r_sma5'].iloc[-1]/df['r_sma20'].iloc[-1]) * 20) + (min(40, (sq_count*5)//15 * 10)))
    
    # 4. Momentum Score
    mom_valid = (df['close'].iloc[-1] > df['vwap'].iloc[-1]) & (df['ema15'].iloc[-1] > df['ema30'].iloc[-1]) & (df['rsi'].iloc[-1] > 55) & \
                (df['volume'].iloc[-1] > 2 * df['v_sma20'].iloc[-1]) & (df['close'].iloc[-1] > df['high'].shift(1).rolling(5).max().iloc[-1])
    
    mom_score = min(100, ((df['volume'].iloc[-1]/df['v_sma20'].iloc[-1]) * 30) + 
                  (30 if df['rsi'].iloc[-1] >= 70 else (20 if df['rsi'].iloc[-1] >= 60 else 10)) +
                  (((df['close'].iloc[-1] - df['high'].shift(1).rolling(5).max().iloc[-1]) / df['high'].shift(1).rolling(5).max().iloc[-1]) * 20) +
                  (((df['close'].iloc[-1] - df['vwap'].iloc[-1]) / df['vwap'].iloc[-1]) * 20)) if mom_valid else 0
    
    final_score = (trend_score*0.25) + (squeeze_score*0.35) + (mom_score*0.40)
    
    return pd.Series({
        'trend_score': trend_score, 'squeeze_score': squeeze_score, 'momentum_score': mom_score,
        'minutes_in_squeeze': sq_count * 5, 'volume_ratio': df['volume'].iloc[-1]/df['v_sma20'].iloc[-1],
        'rsi14': df['rsi'].iloc[-1], 'vwap': df['vwap'].iloc[-1], 'final_score': final_score
    })

# Aliases to prevent breaking the dashboard imports
strategy_pure_squeeze = run_ranking_engine
strategy_momentum_breakout = run_ranking_engine
strategy_combined_elite = run_ranking_engine
strategy_ema_crossover = run_ranking_engine
