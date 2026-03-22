"""
Diagnostic script to test the Swing Scanner pipeline.
Identifies where stocks are being filtered out.
"""
import sys
import os
import logging

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from data_fetcher import get_stock_universe, fetch_ohlcv, passes_universe_filter, fetch_nifty_data
from indicators import compute_all_indicators
from patterns import detect_all_patterns
from signals import generate_signal

def diagnose():
    print("=" * 60)
    print("SWING SCANNER DIAGNOSTIC")
    print("=" * 60)

    # Step 1: Stock universe
    print("\n[1] Fetching stock universe...")
    universe = get_stock_universe()
    print(f"    >> {len(universe)} stocks in universe")

    # Test with first 20 stocks
    test_stocks = universe[:20]
    print(f"    >> Testing with first {len(test_stocks)} stocks\n")

    # Step 2: NIFTY data
    print("[2] Fetching NIFTY data...")
    nifty_df = fetch_nifty_data()
    if nifty_df is not None:
        print(f"    >> NIFTY data: {len(nifty_df)} rows")
    else:
        print("    >> WARNING: NIFTY data fetch FAILED")

    # Step 3: Test each stock
    stats = {
        "fetch_failed": 0,
        "filter_failed": 0,
        "no_patterns": 0,
        "low_confidence": 0,
        "signal_failed": 0,
        "passed": 0,
    }

    print(f"\n[3] Testing {len(test_stocks)} stocks...\n")
    for sym, name, sector, exchange in test_stocks:
        print(f"  --- {sym} ({name}) ---")

        # Fetch data
        df = fetch_ohlcv(sym, period="2y")
        if df is None:
            print(f"    [FAIL] Data fetch FAILED (None returned)")
            stats["fetch_failed"] += 1
            continue
        print(f"    [OK] Data: {len(df)} rows, latest close: Rs.{df['Close'].iloc[-1]:.2f}")

        # Universe filter
        if not passes_universe_filter(df):
            avg_vol = df["Volume"].tail(20).mean()
            print(f"    [FAIL] Universe filter FAILED (price={df['Close'].iloc[-1]:.2f}, avg_vol={avg_vol:.0f})")
            stats["filter_failed"] += 1
            continue
        print(f"    [OK] Universe filter passed")

        # Compute indicators
        df = compute_all_indicators(df)
        rsi_val = df['RSI'].iloc[-1] if 'RSI' in df.columns else 0
        adx_val = df['ADX'].iloc[-1] if 'ADX' in df.columns else 0
        print(f"    [OK] Indicators computed (RSI={rsi_val:.1f}, ADX={adx_val:.1f})")

        # Detect patterns
        patterns = detect_all_patterns(df)
        if not patterns:
            print(f"    [FAIL] No patterns detected")
            stats["no_patterns"] += 1
            continue
        print(f"    [OK] {len(patterns)} pattern(s) found:")
        for p in patterns:
            print(f"      - {p.name} ({p.direction}, conf={p.confidence:.2f})")

        # Check confidence
        best = patterns[0]
        if best.confidence < 0.45:
            print(f"    [FAIL] Best pattern confidence too low: {best.confidence:.2f} < 0.45")
            stats["low_confidence"] += 1
            continue

        # Generate signal
        signal = generate_signal(sym, name, sector, df, best, nifty_df)
        if signal is None:
            print(f"    [FAIL] Signal generation FAILED (likely R:R < 1.5)")
            stats["signal_failed"] += 1
            continue

        sig = signal.to_dict()
        print(f"    [PASS] SIGNAL: entry=Rs.{sig['entry']}, target=Rs.{sig['target']}, SL=Rs.{sig['stop_loss']}, R:R={sig['risk_reward']}, prob={sig['probability']}%")
        stats["passed"] += 1

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    total = len(test_stocks)
    print(f"  Total tested:      {total}")
    print(f"  Data fetch failed: {stats['fetch_failed']}")
    print(f"  Filter failed:     {stats['filter_failed']}")
    print(f"  No patterns:       {stats['no_patterns']}")
    print(f"  Low confidence:    {stats['low_confidence']}")
    print(f"  Signal failed:     {stats['signal_failed']}")
    print(f"  PASSED:            {stats['passed']}")
    print()

    if stats["passed"] == 0:
        print("DIAGNOSIS: Zero results!")
        if stats["fetch_failed"] > total * 0.5:
            print("  >> PRIMARY ISSUE: Data fetching failing for most stocks.")
            print("     Likely cause: yfinance rate limiting or network issues.")
        elif stats["no_patterns"] > total * 0.5:
            print("  >> PRIMARY ISSUE: Pattern detection too strict.")
            print("     Suggestion: Lower confidence thresholds or relax pattern criteria.")
        elif stats["signal_failed"] > 0:
            print("  >> PRIMARY ISSUE: Signal generation filtering (R:R < 1.5).")
            print("     Suggestion: Lower R:R threshold.")
        print()

if __name__ == "__main__":
    diagnose()
