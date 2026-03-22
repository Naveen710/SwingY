"""
Swing Trading Scanner — Technical Indicators Engine
Computes all required technical indicators for the scanning system.
Pure Python implementation (no TA-Lib dependency).
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# EXPONENTIAL MOVING AVERAGES
# ═══════════════════════════════════════════════════════════════

def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Compute Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    """Add EMA 20, 50, 200 to the dataframe."""
    df["EMA20"] = compute_ema(df["Close"], 20)
    df["EMA50"] = compute_ema(df["Close"], 50)
    df["EMA200"] = compute_ema(df["Close"], 200)
    return df


# ═══════════════════════════════════════════════════════════════
# RSI (RELATIVE STRENGTH INDEX)
# ═══════════════════════════════════════════════════════════════

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI using Wilder's smoothing method."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI(14) to the dataframe."""
    df["RSI"] = compute_rsi(df["Close"], 14)
    return df


# ═══════════════════════════════════════════════════════════════
# MACD
# ═══════════════════════════════════════════════════════════════

def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Add MACD, Signal, and Histogram to the dataframe."""
    ema12 = compute_ema(df["Close"], 12)
    ema26 = compute_ema(df["Close"], 26)
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = compute_ema(df["MACD"], 9)
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


# ═══════════════════════════════════════════════════════════════
# BOLLINGER BANDS
# ═══════════════════════════════════════════════════════════════

def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """Add Bollinger Bands to the dataframe."""
    df["BB_Mid"] = df["Close"].rolling(period).mean()
    rolling_std = df["Close"].rolling(period).std()
    df["BB_Upper"] = df["BB_Mid"] + std_dev * rolling_std
    df["BB_Lower"] = df["BB_Mid"] - std_dev * rolling_std
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Mid"]
    return df


# ═══════════════════════════════════════════════════════════════
# ADX (AVERAGE DIRECTIONAL INDEX)
# ═══════════════════════════════════════════════════════════════

def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ADX(14) to the dataframe using Wilder's smoothing."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr)

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    df["ADX"] = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    df["Plus_DI"] = plus_di
    df["Minus_DI"] = minus_di
    return df


# ═══════════════════════════════════════════════════════════════
# ATR (AVERAGE TRUE RANGE)
# ═══════════════════════════════════════════════════════════════

def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ATR(14) to the dataframe."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df["ATR"] = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    df["ATR_Pct"] = df["ATR"] / df["Close"] * 100
    return df


# ═══════════════════════════════════════════════════════════════
# VWAP (VOLUME WEIGHTED AVERAGE PRICE)
# ═══════════════════════════════════════════════════════════════

def add_vwap(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Add rolling VWAP approximation."""
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"]
    cum_tp_vol = (typical_price * vol).rolling(period).sum()
    cum_vol = vol.rolling(period).sum()
    df["VWAP"] = cum_tp_vol / cum_vol.replace(0, np.nan)
    return df


# ═══════════════════════════════════════════════════════════════
# VOLUME ANALYSIS
# ═══════════════════════════════════════════════════════════════

def add_volume_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Add volume moving average and volume ratio."""
    df["Vol_MA20"] = df["Volume"].rolling(20).mean()
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA20"].replace(0, np.nan)
    return df


# ═══════════════════════════════════════════════════════════════
# SWING DETECTION
# ═══════════════════════════════════════════════════════════════

def find_swing_highs(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Find swing high points in the price series."""
    highs = df["High"]
    swing_highs = highs[
        (highs == highs.rolling(2 * window + 1, center=True).max())
    ]
    return swing_highs


def find_swing_lows(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Find swing low points in the price series."""
    lows = df["Low"]
    swing_lows = lows[
        (lows == lows.rolling(2 * window + 1, center=True).min())
    ]
    return swing_lows


def find_support_resistance(df: pd.DataFrame, window: int = 10) -> dict:
    """Find recent support and resistance levels."""
    swing_highs = find_swing_highs(df, window).dropna()
    swing_lows = find_swing_lows(df, window).dropna()

    recent_highs = swing_highs.tail(5).values
    recent_lows = swing_lows.tail(5).values

    resistance = float(np.max(recent_highs)) if len(recent_highs) > 0 else float(df["High"].tail(20).max())
    support = float(np.min(recent_lows)) if len(recent_lows) > 0 else float(df["Low"].tail(20).min())

    return {"resistance": resistance, "support": support}


# ═══════════════════════════════════════════════════════════════
# TREND ANALYSIS
# ═══════════════════════════════════════════════════════════════

def get_trend_direction(df: pd.DataFrame) -> str:
    """Determine overall trend direction from EMAs."""
    if df.empty or "EMA20" not in df.columns:
        return "neutral"

    ema20 = df["EMA20"].iloc[-1]
    ema50 = df["EMA50"].iloc[-1]
    ema200 = df["EMA200"].iloc[-1]

    if ema20 > ema50 > ema200:
        return "strong_bullish"
    elif ema20 > ema50:
        return "bullish"
    elif ema20 < ema50 < ema200:
        return "strong_bearish"
    elif ema20 < ema50:
        return "bearish"
    return "neutral"


def is_ema_aligned_bullish(df: pd.DataFrame) -> bool:
    """Check if EMA 20 > 50 > 200 and price above 200 EMA."""
    if "EMA20" not in df.columns:
        return False
    close = df["Close"].iloc[-1]
    return (
        df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1] > df["EMA200"].iloc[-1]
        and close > df["EMA200"].iloc[-1]
    )


# ═══════════════════════════════════════════════════════════════
# MOMENTUM CHECKS
# ═══════════════════════════════════════════════════════════════

def is_rsi_in_range(df: pd.DataFrame, low: float = 40, high: float = 75) -> bool:
    """Check if RSI is within the desired range."""
    if "RSI" not in df.columns:
        return False
    rsi = df["RSI"].iloc[-1]
    return low <= rsi <= high


def is_rsi_rising(df: pd.DataFrame, candles: int = 3) -> bool:
    """Check if RSI has been rising for the last N candles."""
    if "RSI" not in df.columns or len(df) < candles + 1:
        return False
    rsi_vals = df["RSI"].tail(candles + 1).dropna()
    if len(rsi_vals) < candles + 1:
        return False
    diffs = rsi_vals.diff().dropna()
    rising_count = (diffs > 0).sum()
    return rising_count >= candles - 1  # Allow 1 dip


def has_volume_breakout(df: pd.DataFrame, threshold: float = 1.5) -> bool:
    """Check if current volume is above threshold × 20-day average."""
    if "Vol_Ratio" not in df.columns:
        return False
    return df["Vol_Ratio"].iloc[-1] >= threshold


def has_macd_bullish_crossover(df: pd.DataFrame) -> bool:
    """Check if MACD has bullish crossover (MACD crosses above signal)."""
    if "MACD" not in df.columns or "MACD_Signal" not in df.columns:
        return False
    if len(df) < 3:
        return False
    # Current: MACD > Signal, Previous: MACD <= Signal
    return (
        df["MACD"].iloc[-1] > df["MACD_Signal"].iloc[-1]
        and df["MACD"].iloc[-2] <= df["MACD_Signal"].iloc[-2]
    ) or (
        # Or MACD above signal and histogram increasing
        df["MACD"].iloc[-1] > df["MACD_Signal"].iloc[-1]
        and df["MACD_Hist"].iloc[-1] > df["MACD_Hist"].iloc[-2]
    )


def is_adx_strong(df: pd.DataFrame, threshold: float = 20) -> bool:
    """Check if ADX > threshold (strong trend)."""
    if "ADX" not in df.columns:
        return False
    return df["ADX"].iloc[-1] > threshold


def is_bb_squeeze(df: pd.DataFrame) -> bool:
    """Detect Bollinger Band squeeze (volatility contraction)."""
    if "BB_Width" not in df.columns or len(df) < 60:
        return False
    current_width = df["BB_Width"].iloc[-1]
    percentile_20 = df["BB_Width"].tail(120).quantile(0.2)
    return current_width <= percentile_20


# ═══════════════════════════════════════════════════════════════
# RELATIVE STRENGTH
# ═══════════════════════════════════════════════════════════════

def compute_relative_strength(stock_df: pd.DataFrame, index_df: pd.DataFrame, period: int = 20) -> float:
    """
    Compute relative strength of stock vs index.
    Returns ratio of stock return to index return over period.
    """
    if stock_df is None or index_df is None:
        return 1.0
    try:
        stock_return = (stock_df["Close"].iloc[-1] / stock_df["Close"].iloc[-period] - 1)
        index_return = (index_df["Close"].iloc[-1] / index_df["Close"].iloc[-period] - 1)
        if index_return == 0:
            return 1.0
        return stock_return / index_return if index_return != 0 else 1.0
    except Exception:
        return 1.0


# ═══════════════════════════════════════════════════════════════
# COMPUTE ALL INDICATORS
# ═══════════════════════════════════════════════════════════════

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical indicators for a stock dataframe."""
    df = df.copy()
    df = add_emas(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    df = add_adx(df)
    df = add_atr(df)
    df = add_vwap(df)
    df = add_volume_analysis(df)
    return df
