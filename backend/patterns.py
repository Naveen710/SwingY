"""
Swing Trading Scanner — Chart Pattern Detection Engine
Detects swing trading chart patterns algorithmically using price structure.
"""

import pandas as pd
import numpy as np
import logging
from indicators import (
    find_swing_highs, find_swing_lows, find_support_resistance,
    is_bb_squeeze, is_ema_aligned_bullish, get_trend_direction
)

logger = logging.getLogger(__name__)


class PatternResult:
    """Result of a pattern detection run."""
    def __init__(self, name: str, direction: str, confidence: float,
                 key_levels: dict = None, description: str = ""):
        self.name = name
        self.direction = direction  # "bullish" or "bearish"
        self.confidence = confidence  # 0.0 to 1.0
        self.key_levels = key_levels or {}
        self.description = description

    def to_dict(self):
        return {
            "name": self.name,
            "direction": self.direction,
            "confidence": round(self.confidence, 2),
            "key_levels": self.key_levels,
            "description": self.description,
        }


# ═══════════════════════════════════════════════════════════════
# VOLATILITY CONTRACTION PATTERN (VCP)
# ═══════════════════════════════════════════════════════════════

def detect_vcp(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect Volatility Contraction Pattern (Mark Minervini).
    Price consolidates with decreasing volatility (tightening ranges).
    """
    if len(df) < 60:
        return None

    try:
        # Look at last 60 days for contractions
        recent = df.tail(60)

        # Split into 3 segments of 20 days
        seg1 = recent.iloc[:20]
        seg2 = recent.iloc[20:40]
        seg3 = recent.iloc[40:]

        range1 = (seg1["High"].max() - seg1["Low"].min()) / seg1["Low"].min()
        range2 = (seg2["High"].max() - seg2["Low"].min()) / seg2["Low"].min()
        range3 = (seg3["High"].max() - seg3["Low"].min()) / seg3["Low"].min()

        # Contracting ranges
        if range1 > range2 > range3 and range3 < 0.08:
            # Volume should also be decreasing
            vol1 = seg1["Volume"].mean()
            vol3 = seg3["Volume"].mean()
            vol_decreasing = vol3 < vol1

            confidence = 0.5
            if vol_decreasing:
                confidence += 0.15
            if range1 > 2 * range3:
                confidence += 0.15
            if "EMA50" in df.columns and df["Close"].iloc[-1] > df["EMA50"].iloc[-1]:
                confidence += 0.1

            pivot = float(seg3["High"].max())

            return PatternResult(
                name="VCP (Volatility Contraction)",
                direction="bullish",
                confidence=min(confidence, 0.95),
                key_levels={
                    "pivot": pivot,
                    "support": float(seg3["Low"].min()),
                    "range_contraction": f"{range1:.1%} → {range2:.1%} → {range3:.1%}"
                },
                description=f"Tightening consolidation with ranges contracting from {range1:.1%} to {range3:.1%}. Pivot at ₹{pivot:.2f}."
            )
    except Exception as e:
        logger.debug(f"VCP detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# BULL FLAG
# ═══════════════════════════════════════════════════════════════

def detect_bull_flag(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect Bull Flag pattern.
    Strong upward move (pole) followed by a slight downward channel (flag).
    """
    if len(df) < 40:
        return None

    try:
        recent = df.tail(40)

        # Find the pole: a strong >5% move in 5-15 days
        for pole_end in range(15, 25):
            pole = recent.iloc[:pole_end]
            pole_return = (pole["Close"].iloc[-1] - pole["Close"].iloc[0]) / pole["Close"].iloc[0]

            if pole_return >= 0.05:
                # Flag: next 10-20 days should be a mild pullback
                flag = recent.iloc[pole_end:]
                if len(flag) < 5:
                    continue

                flag_return = (flag["Close"].iloc[-1] - flag["Close"].iloc[0]) / flag["Close"].iloc[0]

                # Flag should retrace less than 50% of pole and have lower volatility
                flag_range = (flag["High"].max() - flag["Low"].min()) / flag["Low"].min()
                pole_range = (pole["High"].max() - pole["Low"].min()) / pole["Low"].min()

                if -0.05 <= flag_return <= 0.02 and flag_range < pole_range * 0.6:
                    # Volume should decrease during flag
                    pole_vol = pole["Volume"].mean()
                    flag_vol = flag["Volume"].mean()

                    confidence = 0.55
                    if flag_vol < pole_vol:
                        confidence += 0.1
                    if pole_return > 0.10:
                        confidence += 0.1
                    if "EMA20" in df.columns and df["Close"].iloc[-1] > df["EMA20"].iloc[-1]:
                        confidence += 0.1

                    breakout_level = float(flag["High"].max())

                    return PatternResult(
                        name="Bull Flag",
                        direction="bullish",
                        confidence=min(confidence, 0.95),
                        key_levels={
                            "breakout": breakout_level,
                            "flag_low": float(flag["Low"].min()),
                            "pole_height": float(pole["Close"].iloc[-1] - pole["Close"].iloc[0]),
                        },
                        description=f"Strong pole (+{pole_return:.1%}) followed by consolidation flag. Breakout above ₹{breakout_level:.2f}."
                    )
                break
    except Exception as e:
        logger.debug(f"Bull Flag detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# ASCENDING TRIANGLE
# ═══════════════════════════════════════════════════════════════

def detect_ascending_triangle(df: pd.DataFrame) -> PatternResult | None:
    """
    Ascending Triangle: flat resistance with rising support (higher lows).
    """
    if len(df) < 40:
        return None

    try:
        recent = df.tail(40)
        swing_highs = find_swing_highs(recent, window=3).dropna()
        swing_lows = find_swing_lows(recent, window=3).dropna()

        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return None

        # Check for flat resistance (highs are similar)
        highs = swing_highs.values[-3:]
        high_range = (max(highs) - min(highs)) / min(highs)

        # Check for rising lows
        lows = swing_lows.values[-3:]
        lows_rising = all(lows[i] < lows[i + 1] for i in range(len(lows) - 1))

        if high_range < 0.03 and lows_rising:
            resistance = float(max(highs))
            latest_support = float(lows[-1])
            confidence = 0.55

            # Price near resistance = higher confidence
            close = float(df["Close"].iloc[-1])
            if close > resistance * 0.97:
                confidence += 0.15

            if "Vol_Ratio" in df.columns and df["Vol_Ratio"].iloc[-1] > 1.2:
                confidence += 0.1

            return PatternResult(
                name="Ascending Triangle",
                direction="bullish",
                confidence=min(confidence, 0.95),
                key_levels={
                    "resistance": resistance,
                    "rising_support": latest_support,
                },
                description=f"Flat resistance at ₹{resistance:.2f} with rising lows. Breakout imminent."
            )
    except Exception as e:
        logger.debug(f"Ascending Triangle detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# DOUBLE BOTTOM
# ═══════════════════════════════════════════════════════════════

def detect_double_bottom(df: pd.DataFrame) -> PatternResult | None:
    """
    Double Bottom: W-pattern where price touches support twice and bounces.
    """
    if len(df) < 50:
        return None

    try:
        recent = df.tail(60)
        swing_lows = find_swing_lows(recent, window=5).dropna()

        if len(swing_lows) < 2:
            return None

        # Find two lows that are close in price (within 3%)
        for i in range(len(swing_lows) - 1):
            low1 = swing_lows.iloc[i]
            low2 = swing_lows.iloc[i + 1]

            price_diff = abs(low1 - low2) / min(low1, low2)

            if price_diff < 0.03:
                # There should be a peak between the two lows
                idx1 = swing_lows.index[i]
                idx2 = swing_lows.index[i + 1]

                between = recent.loc[idx1:idx2]
                if len(between) < 5:
                    continue

                neckline = float(between["High"].max())
                bottom = float(min(low1, low2))
                close = float(df["Close"].iloc[-1])

                # Price should be above the midpoint or near neckline
                if close > (bottom + neckline) / 2:
                    confidence = 0.55
                    if close > neckline * 0.98:
                        confidence += 0.2
                    if "RSI" in df.columns and df["RSI"].iloc[-1] > 50:
                        confidence += 0.1

                    return PatternResult(
                        name="Double Bottom",
                        direction="bullish",
                        confidence=min(confidence, 0.95),
                        key_levels={
                            "neckline": neckline,
                            "bottom": bottom,
                        },
                        description=f"W-pattern with support at ₹{bottom:.2f}. Neckline breakout at ₹{neckline:.2f}."
                    )
    except Exception as e:
        logger.debug(f"Double Bottom detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# BREAKOUT FROM CONSOLIDATION
# ═══════════════════════════════════════════════════════════════

def detect_consolidation_breakout(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect breakout from a consolidation range (sideways movement).
    """
    if len(df) < 30:
        return None

    try:
        # Look at last 30 days for consolidation
        consol = df.iloc[-30:-1]  # Exclude the most recent day
        latest = df.iloc[-1]

        range_high = consol["High"].max()
        range_low = consol["Low"].min()
        range_pct = (range_high - range_low) / range_low

        # Consolidation: range < 10%
        if range_pct < 0.10:
            close = float(latest["Close"])

            # Check if latest close breaks above range
            if close > range_high:
                confidence = 0.55

                # Volume confirmation
                if "Vol_Ratio" in df.columns and df["Vol_Ratio"].iloc[-1] > 1.5:
                    confidence += 0.15

                # Strong trend behind it
                if "EMA50" in df.columns and close > df["EMA50"].iloc[-1]:
                    confidence += 0.1

                return PatternResult(
                    name="Consolidation Breakout",
                    direction="bullish",
                    confidence=min(confidence, 0.95),
                    key_levels={
                        "breakout": float(range_high),
                        "range_low": float(range_low),
                    },
                    description=f"Price breaks above {range_pct:.1%} consolidation range at ₹{range_high:.2f}."
                )
    except Exception as e:
        logger.debug(f"Consolidation breakout detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# EMA PULLBACK (TREND CONTINUATION)
# ═══════════════════════════════════════════════════════════════

def detect_ema_pullback(df: pd.DataFrame) -> PatternResult | None:
    """
    EMA Pullback: Price in uptrend pulls back to 20 or 50 EMA and bounces.
    """
    if len(df) < 60 or "EMA20" not in df.columns:
        return None

    try:
        if not is_ema_aligned_bullish(df):
            return None

        close = df["Close"].iloc[-1]
        ema20 = df["EMA20"].iloc[-1]
        ema50 = df["EMA50"].iloc[-1]

        # Price near EMA20 or EMA50 (within 2%)
        near_ema20 = abs(close - ema20) / ema20 < 0.02
        near_ema50 = abs(close - ema50) / ema50 < 0.03

        if near_ema20 or near_ema50:
            # Confirm bounce: today's close > yesterday's close
            if len(df) >= 2 and close > df["Close"].iloc[-2]:
                ema_name = "20 EMA" if near_ema20 else "50 EMA"
                ema_val = ema20 if near_ema20 else ema50

                confidence = 0.55
                if "RSI" in df.columns and 40 < df["RSI"].iloc[-1] < 60:
                    confidence += 0.1
                if "Vol_Ratio" in df.columns and df["Vol_Ratio"].iloc[-1] > 1.2:
                    confidence += 0.1
                if near_ema20:
                    confidence += 0.1  # Tighter pullback = higher confidence

                return PatternResult(
                    name=f"EMA Pullback ({ema_name})",
                    direction="bullish",
                    confidence=min(confidence, 0.95),
                    key_levels={
                        "ema_support": float(ema_val),
                        "bounce_at": float(close),
                    },
                    description=f"Uptrend pullback to {ema_name} (₹{ema_val:.2f}) with bounce confirmation."
                )
    except Exception as e:
        logger.debug(f"EMA Pullback detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# CUP AND HANDLE
# ═══════════════════════════════════════════════════════════════

def detect_cup_and_handle(df: pd.DataFrame) -> PatternResult | None:
    """
    Cup and Handle: U-shaped recovery followed by a small pullback (handle).
    """
    if len(df) < 80:
        return None

    try:
        # Look at last 80 days
        recent = df.tail(80)

        # Find the cup: previous high → low → recovery to near previous high
        left_rim = recent.iloc[:15]["High"].max()
        cup_bottom_region = recent.iloc[20:50]
        cup_bottom = cup_bottom_region["Low"].min()

        # Right rim region
        right_rim_region = recent.iloc[50:70]
        right_rim = right_rim_region["High"].max()

        # Cup depth should be 10-35%
        cup_depth = (left_rim - cup_bottom) / left_rim
        if not (0.08 <= cup_depth <= 0.40):
            return None

        # Right rim should be near left rim (within 5%)
        rim_diff = abs(right_rim - left_rim) / left_rim
        if rim_diff > 0.06:
            return None

        # Handle: slight pullback in last 10-20 days
        handle = recent.iloc[-15:]
        handle_low = handle["Low"].min()
        handle_pullback = (right_rim - handle_low) / right_rim

        if 0.02 <= handle_pullback <= 0.12:
            confidence = 0.55
            if cup_depth >= 0.15:
                confidence += 0.1
            if "Vol_Ratio" in df.columns:
                handle_vol = handle["Volume"].mean()
                cup_vol = cup_bottom_region["Volume"].mean()
                if handle_vol < cup_vol:
                    confidence += 0.1

            breakout = float(max(left_rim, right_rim))

            return PatternResult(
                name="Cup and Handle",
                direction="bullish",
                confidence=min(confidence, 0.95),
                key_levels={
                    "breakout": breakout,
                    "cup_bottom": float(cup_bottom),
                    "handle_low": float(handle_low),
                },
                description=f"U-shaped cup (depth {cup_depth:.1%}) with handle. Breakout above ₹{breakout:.2f}."
            )
    except Exception as e:
        logger.debug(f"Cup & Handle detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# DOUBLE TOP (BEARISH)
# ═══════════════════════════════════════════════════════════════

def detect_double_top(df: pd.DataFrame) -> PatternResult | None:
    """
    Double Top: M-pattern where price hits resistance twice and fails.
    """
    if len(df) < 50:
        return None

    try:
        recent = df.tail(60)
        swing_highs = find_swing_highs(recent, window=5).dropna()

        if len(swing_highs) < 2:
            return None

        for i in range(len(swing_highs) - 1):
            high1 = swing_highs.iloc[i]
            high2 = swing_highs.iloc[i + 1]

            price_diff = abs(high1 - high2) / max(high1, high2)

            if price_diff < 0.03:
                idx1 = swing_highs.index[i]
                idx2 = swing_highs.index[i + 1]

                between = recent.loc[idx1:idx2]
                if len(between) < 5:
                    continue

                neckline = float(between["Low"].min())
                top = float(max(high1, high2))
                close = float(df["Close"].iloc[-1])

                if close < top * 0.97:
                    confidence = 0.5
                    if close < neckline:
                        confidence += 0.2
                    if "RSI" in df.columns and df["RSI"].iloc[-1] < 50:
                        confidence += 0.1

                    return PatternResult(
                        name="Double Top",
                        direction="bearish",
                        confidence=min(confidence, 0.95),
                        key_levels={
                            "neckline": neckline,
                            "top": top,
                        },
                        description=f"M-pattern with resistance at ₹{top:.2f}. Watch for neckline break below ₹{neckline:.2f}."
                    )
    except Exception as e:
        logger.debug(f"Double Top detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# DESCENDING TRIANGLE (BEARISH)
# ═══════════════════════════════════════════════════════════════

def detect_descending_triangle(df: pd.DataFrame) -> PatternResult | None:
    """
    Descending Triangle: flat support with lower highs.
    """
    if len(df) < 40:
        return None

    try:
        recent = df.tail(40)
        swing_highs = find_swing_highs(recent, window=3).dropna()
        swing_lows = find_swing_lows(recent, window=3).dropna()

        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return None

        lows = swing_lows.values[-3:]
        low_range = (max(lows) - min(lows)) / min(lows)

        highs = swing_highs.values[-3:]
        highs_falling = all(highs[i] > highs[i + 1] for i in range(len(highs) - 1))

        if low_range < 0.03 and highs_falling:
            support = float(min(lows))
            latest_high = float(highs[-1])
            confidence = 0.50

            close = float(df["Close"].iloc[-1])
            if close < support * 1.02:
                confidence += 0.15

            return PatternResult(
                name="Descending Triangle",
                direction="bearish",
                confidence=min(confidence, 0.95),
                key_levels={
                    "support": support,
                    "falling_resistance": latest_high,
                },
                description=f"Flat support at ₹{support:.2f} with lower highs. Breakdown risk."
            )
    except Exception as e:
        logger.debug(f"Descending Triangle detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# BEAR FLAG (BEARISH)
# ═══════════════════════════════════════════════════════════════

def detect_bear_flag(df: pd.DataFrame) -> PatternResult | None:
    """
    Bear Flag: Strong downward move (pole) followed by slight upward channel (flag).
    """
    if len(df) < 40:
        return None

    try:
        recent = df.tail(40)

        for pole_end in range(15, 25):
            pole = recent.iloc[:pole_end]
            pole_return = (pole["Close"].iloc[-1] - pole["Close"].iloc[0]) / pole["Close"].iloc[0]

            if pole_return <= -0.05:
                flag = recent.iloc[pole_end:]
                if len(flag) < 5:
                    continue

                flag_return = (flag["Close"].iloc[-1] - flag["Close"].iloc[0]) / flag["Close"].iloc[0]

                if -0.02 <= flag_return <= 0.05:
                    confidence = 0.50
                    if pole_return < -0.10:
                        confidence += 0.1
                    if "RSI" in df.columns and df["RSI"].iloc[-1] < 45:
                        confidence += 0.1

                    breakdown_level = float(flag["Low"].min())

                    return PatternResult(
                        name="Bear Flag",
                        direction="bearish",
                        confidence=min(confidence, 0.95),
                        key_levels={
                            "breakdown": breakdown_level,
                            "flag_high": float(flag["High"].max()),
                        },
                        description=f"Bearish pole ({pole_return:.1%}) with consolidation flag. Watch breakdown below ₹{breakdown_level:.2f}."
                    )
                break
    except Exception as e:
        logger.debug(f"Bear Flag detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# SUPPORT BOUNCE (MEAN REVERSION)
# ═══════════════════════════════════════════════════════════════

def detect_support_bounce(df: pd.DataFrame) -> PatternResult | None:
    """
    Support Bounce: Price near strong support with reversal candle.
    """
    if len(df) < 50:
        return None

    try:
        sr = find_support_resistance(df.tail(60))
        support = sr["support"]
        close = float(df["Close"].iloc[-1])

        # Within 2% of support
        if abs(close - support) / support < 0.02:
            # Confirm bounce
            if close > df["Close"].iloc[-2]:
                confidence = 0.50
                if "RSI" in df.columns and df["RSI"].iloc[-1] < 35:
                    confidence += 0.15  # Oversold bounce
                if "Vol_Ratio" in df.columns and df["Vol_Ratio"].iloc[-1] > 1.3:
                    confidence += 0.1

                return PatternResult(
                    name="Support Bounce",
                    direction="bullish",
                    confidence=min(confidence, 0.95),
                    key_levels={
                        "support": support,
                        "resistance": sr["resistance"],
                    },
                    description=f"Price bouncing off support at ₹{support:.2f}."
                )
    except Exception as e:
        logger.debug(f"Support Bounce detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# GAP AND GO (MOMENTUM)
# ═══════════════════════════════════════════════════════════════

def detect_gap_up(df: pd.DataFrame) -> PatternResult | None:
    """
    Gap and Go: Stock gaps up >3% with strong volume.
    """
    if len(df) < 5:
        return None

    try:
        prev_close = float(df["Close"].iloc[-2])
        today_open = float(df["Open"].iloc[-1])
        today_close = float(df["Close"].iloc[-1])

        gap_pct = (today_open - prev_close) / prev_close

        if gap_pct >= 0.03:
            # Confirm with close above open (green candle)
            confidence = 0.45
            if today_close > today_open:
                confidence += 0.15
            if "Vol_Ratio" in df.columns and df["Vol_Ratio"].iloc[-1] > 2.0:
                confidence += 0.15
            if gap_pct > 0.05:
                confidence += 0.1

            return PatternResult(
                name="Gap Up Momentum",
                direction="bullish",
                confidence=min(confidence, 0.95),
                key_levels={
                    "gap_start": prev_close,
                    "gap_open": today_open,
                },
                description=f"Gap up of {gap_pct:.1%}. Strong momentum setup."
            )
    except Exception as e:
        logger.debug(f"Gap Up detection error: {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# MASTER PATTERN DETECTOR
# ═══════════════════════════════════════════════════════════════

ALL_DETECTORS = [
    detect_vcp,
    detect_bull_flag,
    detect_ascending_triangle,
    detect_double_bottom,
    detect_consolidation_breakout,
    detect_ema_pullback,
    detect_cup_and_handle,
    detect_support_bounce,
    detect_gap_up,
    # Bearish patterns
    detect_double_top,
    detect_descending_triangle,
    detect_bear_flag,
]


def detect_all_patterns(df: pd.DataFrame) -> list[PatternResult]:
    """
    Run all pattern detectors on a stock dataframe.
    Returns list of detected patterns sorted by confidence.
    """
    detected = []
    for detector in ALL_DETECTORS:
        try:
            result = detector(df)
            if result is not None:
                detected.append(result)
        except Exception as e:
            logger.debug(f"Pattern detector {detector.__name__} error: {e}")

    # Sort by confidence (highest first)
    detected.sort(key=lambda x: x.confidence, reverse=True)
    return detected
