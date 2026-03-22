"""
Swing Trading Scanner — Scanner Worker
Parallel scanner that processes all NSE stocks concurrently.
"""

import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from data_fetcher import (
    get_stock_universe, fetch_ohlcv, fetch_nifty_data,
    passes_universe_filter, FALLBACK_STOCKS
)
from indicators import compute_all_indicators
from patterns import detect_all_patterns
from signals import generate_signal

logger = logging.getLogger(__name__)


class ScannerState:
    """Thread-safe scanner state for progress tracking."""

    def __init__(self):
        self._lock = threading.Lock()
        self.is_running = False
        self.total_stocks = 0
        self.scanned_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.current_stock = ""
        self.results = []
        self.start_time = None
        self.end_time = None
        self.error = None

    def reset(self):
        with self._lock:
            self.is_running = True
            self.total_stocks = 0
            self.scanned_count = 0
            self.passed_count = 0
            self.failed_count = 0
            self.current_stock = ""
            self.results = []
            self.start_time = time.time()
            self.end_time = None
            self.error = None

    def update(self, stock: str = None, passed: bool = False):
        with self._lock:
            self.scanned_count += 1
            if stock:
                self.current_stock = stock
            if passed:
                self.passed_count += 1
            else:
                self.failed_count += 1

    def add_result(self, signal_dict: dict):
        with self._lock:
            self.results.append(signal_dict)

    def finish(self, error: str = None):
        with self._lock:
            self.is_running = False
            self.end_time = time.time()
            self.error = error

    def get_status(self) -> dict:
        with self._lock:
            elapsed = 0
            if self.start_time:
                end = self.end_time or time.time()
                elapsed = round(end - self.start_time, 1)

            return {
                "is_running": self.is_running,
                "total_stocks": self.total_stocks,
                "scanned_count": self.scanned_count,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "current_stock": self.current_stock,
                "results_count": len(self.results),
                "elapsed_seconds": elapsed,
                "error": self.error,
                "progress_pct": round(
                    self.scanned_count / max(self.total_stocks, 1) * 100, 1
                ),
            }

    def get_results(self) -> list:
        with self._lock:
            # Sort by probability (highest first)
            return sorted(self.results, key=lambda x: x.get("probability", 0), reverse=True)


# Global scanner state
scanner_state = ScannerState()


def _scan_single_stock(symbol: str, name: str, sector: str,
                        nifty_df, min_confidence: float = 0.5):
    """Scan a single stock for patterns and generate signals."""
    try:
        # Fetch data
        df = fetch_ohlcv(symbol, period="2y")
        if df is None or not passes_universe_filter(df):
            return None

        # Compute indicators
        df = compute_all_indicators(df)

        # Detect patterns
        patterns = detect_all_patterns(df)
        if not patterns:
            return None

        # Generate signal for the best pattern
        best_pattern = patterns[0]
        if best_pattern.confidence < min_confidence:
            return None

        signal = generate_signal(symbol, name, sector, df, best_pattern, nifty_df)
        if signal is None:
            return None

        result = signal.to_dict()

        # Add OHLCV data for chart
        chart_data = df.tail(120)[["Open", "High", "Low", "Close", "Volume"]].copy()
        chart_data.index = chart_data.index.strftime("%Y-%m-%d")
        result["chart_data"] = chart_data.to_dict(orient="index")

        # Add additional patterns found
        result["all_patterns"] = [p.to_dict() for p in patterns[:3]]

        return result

    except Exception as e:
        logger.debug(f"Error scanning {symbol}: {e}")
        return None


def run_scanner(max_workers: int = 8, min_confidence: float = 0.45,
                test_mode: bool = False, full_mode: bool = False):
    """
    Run the scanner across NSE stocks.
    By default uses curated list of ~150 liquid stocks for speed.
    Set full_mode=True to scan all 2000+ NSE stocks (slow).
    """
    scanner_state.reset()

    try:
        # Choose universe
        if test_mode:
            universe = FALLBACK_STOCKS[:10]
            logger.info("Test mode: scanning 10 stocks")
        elif full_mode:
            universe = get_stock_universe()
            logger.info(f"Full mode: scanning {len(universe)} stocks")
        else:
            # Default: use curated liquid stocks for fast, reliable results
            universe = FALLBACK_STOCKS
            logger.info(f"Curated mode: scanning {len(universe)} liquid stocks")

        scanner_state.total_stocks = len(universe)
        logger.info(f"Starting scan of {len(universe)} stocks with {max_workers} workers")

        # Fetch NIFTY data for relative strength
        nifty_df = fetch_nifty_data()
        if nifty_df is None:
            logger.warning("NIFTY data unavailable, relative strength will be skipped")

        # Parallel scan with timeout
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for sym, name, sector, exchange in universe:
                fut = executor.submit(
                    _scan_single_stock, sym, name, sector, nifty_df, min_confidence
                )
                futures[fut] = (sym, name)

            for future in as_completed(futures, timeout=600):
                sym, name = futures[future]
                try:
                    result = future.result(timeout=30)
                    if result:
                        scanner_state.add_result(result)
                        scanner_state.update(stock=name, passed=True)
                        logger.info(f"SIGNAL: {sym} - {result.get('pattern', {}).get('name', 'Unknown')}")
                    else:
                        scanner_state.update(stock=name, passed=False)
                except TimeoutError:
                    logger.warning(f"Timeout scanning {sym}")
                    scanner_state.update(stock=name, passed=False)
                except Exception as e:
                    logger.debug(f"Future error {sym}: {e}")
                    scanner_state.update(stock=name, passed=False)

        scanner_state.finish()
        logger.info(
            f"Scan complete: {scanner_state.passed_count} opportunities found "
            f"out of {scanner_state.scanned_count} stocks in "
            f"{scanner_state.get_status()['elapsed_seconds']}s"
        )

    except TimeoutError:
        logger.error("Scanner timed out after 600 seconds")
        scanner_state.finish(error="Scanner timed out")
    except Exception as e:
        logger.error(f"Scanner error: {e}")
        scanner_state.finish(error=str(e))
