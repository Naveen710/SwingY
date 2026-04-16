"""Quick import test for all backend modules."""
import sys
try:
    from data_fetcher import get_stock_universe, fetch_ohlcv
    print("[OK] data_fetcher")
except Exception as e:
    print(f"[FAIL] data_fetcher: {e}")

try:
    from indicators import compute_all_indicators
    print("[OK] indicators")
except Exception as e:
    print(f"[FAIL] indicators: {e}")

try:
    from patterns import detect_all_patterns, PatternResult
    print("[OK] patterns")
except Exception as e:
    print(f"[FAIL] patterns: {e}")

try:
    from signals import generate_signal, TradeSignal
    print("[OK] signals")
except Exception as e:
    print(f"[FAIL] signals: {e}")

try:
    from backtester import run_backtest
    print("[OK] backtester")
except Exception as e:
    print(f"[FAIL] backtester: {e}")

try:
    from scanner_worker import run_scanner, scanner_state
    print("[OK] scanner_worker")
except Exception as e:
    print(f"[FAIL] scanner_worker: {e}")

try:
    from nifty500 import NIFTY_500_STOCKS
    print(f"[OK] nifty500 ({len(NIFTY_500_STOCKS)} stocks)")
except Exception as e:
    print(f"[FAIL] nifty500: {e}")

try:
    from main import app
    print("[OK] main (FastAPI app)")
except Exception as e:
    print(f"[FAIL] main: {e}")

print("\nAll imports tested.")
