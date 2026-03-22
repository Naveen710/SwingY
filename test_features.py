"""Quick test to verify estimated_days and NIFTY 500 integration."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from nifty500 import NIFTY_500_STOCKS
from data_fetcher import fetch_ohlcv, fetch_nifty_data, passes_universe_filter
from indicators import compute_all_indicators
from patterns import detect_all_patterns
from signals import generate_signal

print(f"NIFTY 500 list: {len(NIFTY_500_STOCKS)} stocks")

# Test with 5 stocks
test_stocks = NIFTY_500_STOCKS[:5]
nifty_df = fetch_nifty_data()

for sym, name, sector, exchange in test_stocks:
    print(f"\n--- {sym} ({name}) ---")
    df = fetch_ohlcv(sym, period="2y")
    if df is None:
        print("  Data fetch FAILED")
        continue
    
    if not passes_universe_filter(df):
        print("  Filter FAILED")
        continue
    
    df = compute_all_indicators(df)
    patterns = detect_all_patterns(df)
    if not patterns:
        print("  No patterns")
        continue
    
    best = patterns[0]
    signal = generate_signal(sym, name, sector, df, best, nifty_df)
    if signal is None:
        print("  Signal generation failed")
        continue
    
    s = signal.to_dict()
    print(f"  Entry: Rs.{s['entry']}, Target: Rs.{s['target']}")
    print(f"  R:R: {s['risk_reward']}, Probability: {s['probability']}%")
    print(f"  ** Estimated Days: {s['estimated_days']} trading days **")
    print(f"  Profit on 1L: Rs.{s['profit_on_1lakh']}")

print("\nDone!")
