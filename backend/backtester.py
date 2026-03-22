"""
Swing Trading Scanner — Backtesting Engine
Tests pattern success rates against historical data.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BacktestResult:
    """Result of backtesting a pattern on historical data."""

    def __init__(self, pattern_name: str):
        self.pattern_name = pattern_name
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.win_rate = 0.0
        self.avg_return = 0.0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.max_drawdown = 0.0
        self.profit_factor = 0.0
        self.trades = []

    def to_dict(self):
        return {
            "pattern_name": self.pattern_name,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate * 100, 1),
            "avg_return": round(self.avg_return, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "profit_factor": round(self.profit_factor, 2),
        }


def backtest_breakout(df: pd.DataFrame, lookback_days: int = 20,
                       hold_days: int = 15, stop_pct: float = 0.05) -> list:
    """
    Backtest consolidation breakout strategy on historical data.
    Returns list of trade results.
    """
    trades = []
    if len(df) < lookback_days + hold_days + 50:
        return trades

    # Start from day 50 to have enough history
    for i in range(50, len(df) - hold_days):
        window = df.iloc[i - lookback_days:i]
        range_high = window["High"].max()
        range_low = window["Low"].min()
        range_pct = (range_high - range_low) / range_low

        # Check for consolidation
        if range_pct < 0.10:
            close = df["Close"].iloc[i]
            # Breakout above range
            if close > range_high:
                entry = float(close)
                stop_loss = entry * (1 - stop_pct)

                # Track trade for hold_days
                future = df.iloc[i:i + hold_days]
                if len(future) < hold_days:
                    continue

                # Check if stop hit
                min_price = future["Low"].min()
                if min_price <= stop_loss:
                    # Stopped out
                    exit_price = stop_loss
                    pnl = (exit_price - entry) / entry * 100
                    trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "result": "loss"})
                else:
                    exit_price = float(future["Close"].iloc[-1])
                    pnl = (exit_price - entry) / entry * 100
                    result = "win" if pnl > 0 else "loss"
                    trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "result": result})

    return trades


def backtest_ema_pullback(df: pd.DataFrame, hold_days: int = 15, stop_pct: float = 0.04) -> list:
    """Backtest EMA pullback strategy."""
    trades = []
    if len(df) < 250:
        return trades

    from indicators import compute_ema

    ema20 = compute_ema(df["Close"], 20)
    ema50 = compute_ema(df["Close"], 50)
    ema200 = compute_ema(df["Close"], 200)

    for i in range(210, len(df) - hold_days):
        # Check EMA alignment
        if ema20.iloc[i] > ema50.iloc[i] > ema200.iloc[i]:
            close = df["Close"].iloc[i]
            # Price near EMA20 (within 2%)
            if abs(close - ema20.iloc[i]) / ema20.iloc[i] < 0.02:
                # Bounce confirmation
                if close > df["Close"].iloc[i - 1]:
                    entry = float(close)
                    stop_loss = entry * (1 - stop_pct)

                    future = df.iloc[i:i + hold_days]
                    if len(future) < hold_days:
                        continue

                    min_price = future["Low"].min()
                    if min_price <= stop_loss:
                        exit_price = stop_loss
                        pnl = (exit_price - entry) / entry * 100
                        trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "result": "loss"})
                    else:
                        exit_price = float(future["Close"].iloc[-1])
                        pnl = (exit_price - entry) / entry * 100
                        result = "win" if pnl > 0 else "loss"
                        trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "result": result})

    return trades


def backtest_volume_breakout(df: pd.DataFrame, hold_days: int = 10, stop_pct: float = 0.04) -> list:
    """Backtest volume breakout strategy."""
    trades = []
    if len(df) < 100:
        return trades

    vol_ma = df["Volume"].rolling(20).mean()

    for i in range(30, len(df) - hold_days):
        # Volume spike > 2x average
        if df["Volume"].iloc[i] > 2 * vol_ma.iloc[i]:
            close = df["Close"].iloc[i]
            prev_close = df["Close"].iloc[i - 1]

            # Also need price breakout (close above 20-day high)
            high_20 = df["High"].iloc[i - 20:i].max()
            if close > high_20 and close > prev_close:
                entry = float(close)
                stop_loss = entry * (1 - stop_pct)

                future = df.iloc[i:i + hold_days]
                if len(future) < hold_days:
                    continue

                min_price = future["Low"].min()
                if min_price <= stop_loss:
                    exit_price = stop_loss
                    pnl = (exit_price - entry) / entry * 100
                    trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "result": "loss"})
                else:
                    exit_price = float(future["Close"].iloc[-1])
                    pnl = (exit_price - entry) / entry * 100
                    result = "win" if pnl > 0 else "loss"
                    trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "result": result})

    return trades


def _compute_stats(trades: list) -> dict:
    """Compute backtest statistics from a list of trades."""
    if not trades:
        return {
            "total": 0, "wins": 0, "losses": 0,
            "win_rate": 0, "avg_return": 0,
            "avg_win": 0, "avg_loss": 0,
            "max_drawdown": 0, "profit_factor": 0,
        }

    wins = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]

    win_pnls = [t["pnl"] for t in wins]
    loss_pnls = [t["pnl"] for t in losses]
    all_pnls = [t["pnl"] for t in trades]

    avg_win = np.mean(win_pnls) if win_pnls else 0
    avg_loss = abs(np.mean(loss_pnls)) if loss_pnls else 0

    gross_profit = sum(win_pnls) if win_pnls else 0
    gross_loss = abs(sum(loss_pnls)) if loss_pnls else 0.01

    # Max drawdown from cumulative PnL
    cum_pnl = np.cumsum(all_pnls)
    peak = np.maximum.accumulate(cum_pnl)
    drawdown = peak - cum_pnl
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0

    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_return": round(np.mean(all_pnls), 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_dd, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
    }


def run_backtest(df: pd.DataFrame, strategy: str = "all") -> dict:
    """
    Run backtest for specified strategy or all strategies.
    Returns dict of strategy -> stats.
    """
    results = {}

    if strategy in ("all", "breakout"):
        trades = backtest_breakout(df)
        results["Consolidation Breakout"] = _compute_stats(trades)

    if strategy in ("all", "ema_pullback"):
        trades = backtest_ema_pullback(df)
        results["EMA Pullback"] = _compute_stats(trades)

    if strategy in ("all", "volume_breakout"):
        trades = backtest_volume_breakout(df)
        results["Volume Breakout"] = _compute_stats(trades)

    return results
