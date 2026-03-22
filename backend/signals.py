"""
Swing Trading Scanner — Trade Signal Generator
Generates entry, stop loss, target, R:R, probability, and profitability.
"""

import pandas as pd
import numpy as np
import logging
from indicators import (
    is_ema_aligned_bullish, is_rsi_in_range, is_rsi_rising,
    has_volume_breakout, has_macd_bullish_crossover, is_adx_strong,
    is_bb_squeeze, compute_relative_strength, get_trend_direction
)
from patterns import PatternResult

logger = logging.getLogger(__name__)


class TradeSignal:
    """A trade signal with entry, stop loss, target, and probability."""

    def __init__(self, symbol: str, name: str, sector: str):
        self.symbol = symbol
        self.name = name
        self.sector = sector
        self.current_price = 0.0
        self.entry = 0.0
        self.stop_loss = 0.0
        self.target = 0.0
        self.risk_reward = 0.0
        self.probability = 0.0
        self.expected_return_pct = 0.0
        self.profit_on_1lakh = 0.0
        self.pattern = None  # PatternResult
        self.direction = "bullish"
        self.confluence_factors = []
        self.confidence_score = 0.0

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "current_price": round(self.current_price, 2),
            "entry": round(self.entry, 2),
            "stop_loss": round(self.stop_loss, 2),
            "target": round(self.target, 2),
            "risk_reward": round(self.risk_reward, 2),
            "probability": round(self.probability * 100, 1),
            "expected_return_pct": round(self.expected_return_pct, 2),
            "profit_on_1lakh": round(self.profit_on_1lakh, 0),
            "direction": self.direction,
            "pattern": self.pattern.to_dict() if self.pattern else None,
            "confluence_factors": self.confluence_factors,
            "confidence_score": round(self.confidence_score, 2),
        }


def _calculate_stop_loss(df: pd.DataFrame, pattern: PatternResult, entry: float) -> float:
    """Calculate stop loss based on pattern and ATR."""
    # Use pattern key levels if available
    if pattern.direction == "bullish":
        # Try pattern-specific levels
        if "flag_low" in pattern.key_levels:
            return pattern.key_levels["flag_low"] * 0.99
        if "support" in pattern.key_levels:
            return pattern.key_levels["support"] * 0.99
        if "cup_bottom" in pattern.key_levels:
            return max(pattern.key_levels["handle_low"] * 0.99,
                      entry * 0.93)
        if "bottom" in pattern.key_levels:
            return pattern.key_levels["bottom"] * 0.99
        if "ema_support" in pattern.key_levels:
            return pattern.key_levels["ema_support"] * 0.98
        if "range_low" in pattern.key_levels:
            return pattern.key_levels["range_low"] * 0.99

    # ATR-based fallback
    if "ATR" in df.columns:
        atr = df["ATR"].iloc[-1]
        if pattern.direction == "bullish":
            return entry - (2.0 * atr)
        else:
            return entry + (2.0 * atr)

    # Percentage-based fallback
    if pattern.direction == "bullish":
        return entry * 0.95
    return entry * 1.05


def _calculate_target(df: pd.DataFrame, pattern: PatternResult, entry: float, stop_loss: float) -> float:
    """Calculate target price based on pattern and risk/reward."""
    risk = abs(entry - stop_loss)

    if pattern.direction == "bullish":
        # Pattern-specific targets
        if pattern.name == "Cup and Handle" and "breakout" in pattern.key_levels:
            cup_depth = pattern.key_levels.get("breakout", entry) - pattern.key_levels.get("cup_bottom", entry * 0.85)
            return entry + cup_depth  # Measured move

        if "pole_height" in pattern.key_levels:
            return entry + pattern.key_levels["pole_height"]  # Flag measured move

        if "resistance" in pattern.key_levels:
            target = pattern.key_levels["resistance"]
            if target > entry * 1.03:
                return target

        if "neckline" in pattern.key_levels and "bottom" in pattern.key_levels:
            depth = pattern.key_levels["neckline"] - pattern.key_levels["bottom"]
            return pattern.key_levels["neckline"] + depth

        # Default: 2:1 or 3:1 R:R
        return entry + (risk * 2.5)
    else:
        return entry - (risk * 2.5)


def _calculate_probability(df: pd.DataFrame, pattern: PatternResult, nifty_df=None) -> float:
    """
    Calculate multi-factor probability score based on confluence of signals.
    Returns value between 0.0 and 1.0.
    """
    base_prob = pattern.confidence
    factors = []
    bonus = 0.0

    # Trend alignment
    if is_ema_aligned_bullish(df):
        bonus += 0.05
        factors.append("EMA Alignment ✓")

    # RSI in sweet spot
    if is_rsi_in_range(df, 40, 70):
        bonus += 0.03
        factors.append("RSI in range ✓")

    if is_rsi_rising(df):
        bonus += 0.03
        factors.append("RSI Rising ✓")

    # Volume confirmation
    if has_volume_breakout(df, 1.3):
        bonus += 0.05
        factors.append("Volume Breakout ✓")

    # MACD
    if has_macd_bullish_crossover(df):
        bonus += 0.04
        factors.append("MACD Crossover ✓")

    # ADX trend strength
    if is_adx_strong(df, 20):
        bonus += 0.03
        factors.append("Strong Trend (ADX) ✓")

    # BB squeeze (pending breakout)
    if is_bb_squeeze(df):
        bonus += 0.03
        factors.append("BB Squeeze ✓")

    # Relative strength vs NIFTY
    if nifty_df is not None:
        rs = compute_relative_strength(df, nifty_df)
        if rs > 1.2:
            bonus += 0.04
            factors.append(f"RS vs NIFTY: {rs:.1f} ✓")

    probability = min(base_prob + bonus, 0.90)
    return probability, factors


def generate_signal(
    symbol: str, name: str, sector: str,
    df: pd.DataFrame, pattern: PatternResult,
    nifty_df: pd.DataFrame = None
) -> TradeSignal | None:
    """
    Generate a complete trade signal for a stock with a detected pattern.
    """
    try:
        signal = TradeSignal(symbol, name, sector)
        signal.pattern = pattern
        signal.direction = pattern.direction

        close = float(df["Close"].iloc[-1])
        signal.current_price = close

        # Entry
        if pattern.direction == "bullish":
            # Entry at current price or breakout level
            breakout = pattern.key_levels.get("breakout", pattern.key_levels.get("pivot", close))
            signal.entry = max(close, breakout) if breakout > close * 0.98 else close
        else:
            signal.entry = close

        # Stop Loss
        signal.stop_loss = _calculate_stop_loss(df, pattern, signal.entry)

        # Target
        signal.target = _calculate_target(df, pattern, signal.entry, signal.stop_loss)

        # Risk Reward
        risk = abs(signal.entry - signal.stop_loss)
        reward = abs(signal.target - signal.entry)
        signal.risk_reward = round(reward / risk, 2) if risk > 0 else 0

        # Skip if R:R is too low
        if signal.risk_reward < 1.5:
            return None

        # Probability
        signal.probability, signal.confluence_factors = _calculate_probability(df, pattern, nifty_df)
        signal.confidence_score = signal.probability

        # Expected return & profit on ₹1,00,000
        if pattern.direction == "bullish":
            signal.expected_return_pct = ((signal.target - signal.entry) / signal.entry) * 100
        else:
            signal.expected_return_pct = ((signal.entry - signal.target) / signal.entry) * 100

        signal.profit_on_1lakh = 100000 * (signal.expected_return_pct / 100)

        return signal

    except Exception as e:
        logger.debug(f"Signal generation error for {symbol}: {e}")
        return None
