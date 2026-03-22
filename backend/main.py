"""
Swing Trading Scanner — FastAPI Backend
Main API server with endpoints for scanning, stock data, and backtesting.
"""

import logging
import threading
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from data_fetcher import get_stock_universe, fetch_ohlcv, passes_universe_filter
from indicators import compute_all_indicators
from patterns import detect_all_patterns
from signals import generate_signal
from backtester import run_backtest
from scanner_worker import run_scanner, scanner_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Swing Trading Scanner API",
    description="AI-powered NSE swing trading scanner",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "swing-scanner"}


# ═══════════════════════════════════════════════════════════════
# SCANNER ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/scan")
async def start_scan(
    test: bool = Query(False, description="Test mode (scan only 10 stocks)"),
    min_confidence: float = Query(0.45, description="Minimum pattern confidence"),
    max_workers: int = Query(15, description="Number of parallel workers"),
):
    """Start a full scanner run across all NSE stocks."""
    if scanner_state.is_running:
        return JSONResponse(
            status_code=409,
            content={"error": "Scanner is already running", "status": scanner_state.get_status()}
        )

    # Run scanner in background thread
    thread = threading.Thread(
        target=run_scanner,
        kwargs={
            "max_workers": max_workers,
            "min_confidence": min_confidence,
            "test_mode": test,
        },
        daemon=True
    )
    thread.start()

    return {
        "message": "Scanner started",
        "status": scanner_state.get_status()
    }


@app.get("/api/status")
async def get_scan_status():
    """Get current scanner progress and status."""
    return scanner_state.get_status()


@app.get("/api/results")
async def get_scan_results(
    direction: str = Query(None, description="Filter: bullish/bearish"),
    sector: str = Query(None, description="Filter by sector"),
    min_rr: float = Query(None, description="Minimum risk:reward ratio"),
    min_prob: float = Query(None, description="Minimum probability %"),
    limit: int = Query(50, description="Max results"),
):
    """Get scanner results with optional filters."""
    results = scanner_state.get_results()

    # Apply filters
    if direction:
        results = [r for r in results if r.get("direction") == direction]
    if sector:
        results = [r for r in results if r.get("sector", "").lower() == sector.lower()]
    if min_rr:
        results = [r for r in results if r.get("risk_reward", 0) >= min_rr]
    if min_prob:
        results = [r for r in results if r.get("probability", 0) >= min_prob]

    return {
        "count": len(results[:limit]),
        "total": len(results),
        "results": results[:limit],
    }


# ═══════════════════════════════════════════════════════════════
# STOCK ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/stocks")
async def get_stocks():
    """Get the full stock universe."""
    universe = get_stock_universe()
    sectors = sorted(set(s[2] for s in universe))
    return {
        "count": len(universe),
        "sectors": sectors,
        "stocks": [
            {"symbol": s[0], "name": s[1], "sector": s[2], "exchange": s[3]}
            for s in universe
        ]
    }


@app.get("/api/stock/{symbol}")
async def get_stock_detail(symbol: str):
    """Get detailed stock data including indicators, patterns, and chart data."""
    # Ensure .NS suffix
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    df = fetch_ohlcv(symbol, period="2y")
    if df is None:
        return JSONResponse(status_code=404, content={"error": f"No data for {symbol}"})

    # Compute indicators
    df = compute_all_indicators(df)

    # Detect patterns
    patterns = detect_all_patterns(df)

    # Latest indicators
    latest = df.iloc[-1]
    indicators = {}
    for col in ["EMA20", "EMA50", "EMA200", "RSI", "MACD", "MACD_Signal",
                "ADX", "ATR", "ATR_Pct", "BB_Upper", "BB_Lower", "BB_Width",
                "VWAP", "Vol_Ratio"]:
        if col in df.columns:
            val = latest[col]
            indicators[col] = round(float(val), 2) if not (val != val) else None

    # Generate signal if pattern found
    signal = None
    if patterns:
        from data_fetcher import fetch_nifty_data
        nifty_df = fetch_nifty_data()
        # Find stock name from universe
        universe = get_stock_universe()
        name = symbol
        sector = "Unknown"
        for s in universe:
            if s[0] == symbol:
                name = s[1]
                sector = s[2]
                break
        sig = generate_signal(symbol, name, sector, df, patterns[0], nifty_df)
        if sig:
            signal = sig.to_dict()

    # Chart data (last 250 days)
    chart_df = df.tail(250)[["Open", "High", "Low", "Close", "Volume"]].copy()
    chart_df.index = chart_df.index.strftime("%Y-%m-%d")

    # EMA data for chart overlay
    ema_data = {}
    for ema_col in ["EMA20", "EMA50", "EMA200"]:
        if ema_col in df.columns:
            ema_series = df[ema_col].tail(250).dropna()
            ema_series.index = ema_series.index.strftime("%Y-%m-%d")
            ema_data[ema_col] = {k: round(v, 2) for k, v in ema_series.to_dict().items()}

    return {
        "symbol": symbol,
        "current_price": round(float(latest["Close"]), 2),
        "indicators": indicators,
        "patterns": [p.to_dict() for p in patterns],
        "signal": signal,
        "chart_data": chart_df.to_dict(orient="index"),
        "ema_data": ema_data,
    }


# ═════════════════════════════════════════════════════════════
# BACKTEST ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/backtest/{symbol}")
async def get_backtest(symbol: str):
    """Run backtest on a specific stock."""
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    df = fetch_ohlcv(symbol, period="5y")
    if df is None:
        return JSONResponse(status_code=404, content={"error": f"No data for {symbol}"})

    results = run_backtest(df, strategy="all")
    return {
        "symbol": symbol,
        "strategies": results,
    }


@app.get("/api/sectors")
async def get_sectors():
    """Get list of all sectors."""
    universe = get_stock_universe()
    sectors = sorted(set(s[2] for s in universe))
    return {"sectors": sectors}


# ═══════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
