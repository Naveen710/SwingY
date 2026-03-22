"""
Swing Trading Scanner — Data Fetcher
Fetches ALL NSE stock symbols and OHLCV data via yfinance with caching.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io
import os
import json
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}

# ═══════════════════════════════════════════════════════════════
# CURATED FALLBACK STOCK LIST (200+ liquid NSE stocks)
# ═══════════════════════════════════════════════════════════════

FALLBACK_STOCKS = [
    # ── BANKING & FINANCIAL ──
    ("HDFCBANK.NS", "HDFC Bank", "Banking", "NSE"),
    ("ICICIBANK.NS", "ICICI Bank", "Banking", "NSE"),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank", "Banking", "NSE"),
    ("SBIN.NS", "State Bank of India", "Banking", "NSE"),
    ("AXISBANK.NS", "Axis Bank", "Banking", "NSE"),
    ("INDUSINDBK.NS", "IndusInd Bank", "Banking", "NSE"),
    ("BANKBARODA.NS", "Bank of Baroda", "Banking", "NSE"),
    ("PNB.NS", "Punjab National Bank", "Banking", "NSE"),
    ("FEDERALBNK.NS", "Federal Bank", "Banking", "NSE"),
    ("IDFCFIRSTB.NS", "IDFC First Bank", "Banking", "NSE"),
    ("AUBANK.NS", "AU Small Finance Bank", "Banking", "NSE"),
    ("BANDHANBNK.NS", "Bandhan Bank", "Banking", "NSE"),
    ("BAJFINANCE.NS", "Bajaj Finance", "NBFC", "NSE"),
    ("BAJAJFINSV.NS", "Bajaj Finserv", "NBFC", "NSE"),
    ("CHOLAFIN.NS", "Cholamandalam Investment", "NBFC", "NSE"),
    ("MUTHOOTFIN.NS", "Muthoot Finance", "NBFC", "NSE"),
    ("M&MFIN.NS", "Mahindra Finance", "NBFC", "NSE"),
    ("LICHSGFIN.NS", "LIC Housing Finance", "NBFC", "NSE"),
    ("RECLTD.NS", "REC", "Financial Services", "NSE"),
    ("PFC.NS", "Power Finance Corp", "Financial Services", "NSE"),
    ("IRFC.NS", "Indian Railway Finance", "Financial Services", "NSE"),
    ("HDFCLIFE.NS", "HDFC Life Insurance", "Insurance", "NSE"),
    ("SBILIFE.NS", "SBI Life Insurance", "Insurance", "NSE"),
    ("ICICIPRULI.NS", "ICICI Prudential Life", "Insurance", "NSE"),

    # ── IT / TECH ──
    ("TCS.NS", "Tata Consultancy Services", "IT", "NSE"),
    ("INFY.NS", "Infosys", "IT", "NSE"),
    ("WIPRO.NS", "Wipro", "IT", "NSE"),
    ("HCLTECH.NS", "HCL Technologies", "IT", "NSE"),
    ("TECHM.NS", "Tech Mahindra", "IT", "NSE"),
    ("LTIM.NS", "LTIMindtree", "IT", "NSE"),
    ("MPHASIS.NS", "Mphasis", "IT", "NSE"),
    ("COFORGE.NS", "Coforge", "IT", "NSE"),
    ("PERSISTENT.NS", "Persistent Systems", "IT", "NSE"),
    ("LTTS.NS", "L&T Technology Services", "IT", "NSE"),

    # ── AUTOMOBILE ──
    ("MARUTI.NS", "Maruti Suzuki", "Automobile", "NSE"),
    ("TATAMOTORS.NS", "Tata Motors", "Automobile", "NSE"),
    ("M&M.NS", "Mahindra & Mahindra", "Automobile", "NSE"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto", "Automobile", "NSE"),
    ("HEROMOTOCO.NS", "Hero MotoCorp", "Automobile", "NSE"),
    ("EICHERMOT.NS", "Eicher Motors", "Automobile", "NSE"),
    ("ASHOKLEY.NS", "Ashok Leyland", "Automobile", "NSE"),
    ("TVSMOTOR.NS", "TVS Motor", "Automobile", "NSE"),

    # ── PHARMA & HEALTHCARE ──
    ("SUNPHARMA.NS", "Sun Pharma", "Pharma", "NSE"),
    ("DRREDDY.NS", "Dr Reddy's Labs", "Pharma", "NSE"),
    ("CIPLA.NS", "Cipla", "Pharma", "NSE"),
    ("DIVISLAB.NS", "Divi's Labs", "Pharma", "NSE"),
    ("APOLLOHOSP.NS", "Apollo Hospitals", "Healthcare", "NSE"),
    ("MAXHEALTH.NS", "Max Healthcare", "Healthcare", "NSE"),
    ("BIOCON.NS", "Biocon", "Pharma", "NSE"),
    ("LUPIN.NS", "Lupin", "Pharma", "NSE"),
    ("AUROPHARMA.NS", "Aurobindo Pharma", "Pharma", "NSE"),
    ("TORNTPHARM.NS", "Torrent Pharma", "Pharma", "NSE"),

    # ── FMCG ──
    ("HINDUNILVR.NS", "Hindustan Unilever", "FMCG", "NSE"),
    ("ITC.NS", "ITC", "FMCG", "NSE"),
    ("NESTLEIND.NS", "Nestle India", "FMCG", "NSE"),
    ("BRITANNIA.NS", "Britannia Industries", "FMCG", "NSE"),
    ("TATACONSUM.NS", "Tata Consumer Products", "FMCG", "NSE"),
    ("DABUR.NS", "Dabur India", "FMCG", "NSE"),
    ("MARICO.NS", "Marico", "FMCG", "NSE"),
    ("COLPAL.NS", "Colgate Palmolive", "FMCG", "NSE"),
    ("GODREJCP.NS", "Godrej Consumer Products", "FMCG", "NSE"),

    # ── ENERGY / OIL & GAS ──
    ("RELIANCE.NS", "Reliance Industries", "Conglomerate", "NSE"),
    ("ONGC.NS", "ONGC", "Oil & Gas", "NSE"),
    ("IOC.NS", "Indian Oil Corp", "Oil & Gas", "NSE"),
    ("BPCL.NS", "Bharat Petroleum", "Oil & Gas", "NSE"),
    ("GAIL.NS", "GAIL India", "Oil & Gas", "NSE"),
    ("NTPC.NS", "NTPC", "Power", "NSE"),
    ("POWERGRID.NS", "Power Grid Corp", "Power", "NSE"),
    ("TATAPOWER.NS", "Tata Power", "Power", "NSE"),
    ("ADANIGREEN.NS", "Adani Green Energy", "Power", "NSE"),
    ("COALINDIA.NS", "Coal India", "Mining", "NSE"),

    # ── METALS & MINING ──
    ("TATASTEEL.NS", "Tata Steel", "Metals", "NSE"),
    ("JSWSTEEL.NS", "JSW Steel", "Metals", "NSE"),
    ("HINDALCO.NS", "Hindalco", "Metals", "NSE"),
    ("VEDL.NS", "Vedanta", "Metals", "NSE"),
    ("NMDC.NS", "NMDC", "Metals", "NSE"),
    ("NATIONALUM.NS", "National Aluminium", "Metals", "NSE"),

    # ── INFRASTRUCTURE & CAPITAL GOODS ──
    ("LT.NS", "Larsen & Toubro", "Infrastructure", "NSE"),
    ("ADANIENT.NS", "Adani Enterprises", "Conglomerate", "NSE"),
    ("ADANIPORTS.NS", "Adani Ports", "Infrastructure", "NSE"),
    ("ULTRACEMCO.NS", "UltraTech Cement", "Cement", "NSE"),
    ("SHREECEM.NS", "Shree Cement", "Cement", "NSE"),
    ("AMBUJACEM.NS", "Ambuja Cement", "Cement", "NSE"),
    ("ACC.NS", "ACC", "Cement", "NSE"),
    ("SIEMENS.NS", "Siemens", "Capital Goods", "NSE"),
    ("ABB.NS", "ABB India", "Capital Goods", "NSE"),
    ("HAL.NS", "Hindustan Aeronautics", "Defence", "NSE"),
    ("BEL.NS", "Bharat Electronics", "Defence", "NSE"),
    ("BHEL.NS", "BHEL", "Capital Goods", "NSE"),
    ("CUMMINSIND.NS", "Cummins India", "Capital Goods", "NSE"),

    # ── CHEMICALS ──
    ("PIDILITIND.NS", "Pidilite Industries", "Chemicals", "NSE"),
    ("SRF.NS", "SRF", "Chemicals", "NSE"),
    ("ATUL.NS", "Atul", "Chemicals", "NSE"),
    ("NAVINFLUOR.NS", "Navin Fluorine", "Chemicals", "NSE"),
    ("DEEPAKNTR.NS", "Deepak Nitrite", "Chemicals", "NSE"),

    # ── REAL ESTATE ──
    ("DLF.NS", "DLF", "Real Estate", "NSE"),
    ("GODREJPROP.NS", "Godrej Properties", "Real Estate", "NSE"),
    ("OBEROIRLTY.NS", "Oberoi Realty", "Real Estate", "NSE"),
    ("PRESTIGE.NS", "Prestige Estates", "Real Estate", "NSE"),

    # ── TELECOM & MEDIA ──
    ("BHARTIARTL.NS", "Bharti Airtel", "Telecom", "NSE"),
    ("IDEA.NS", "Vodafone Idea", "Telecom", "NSE"),

    # ── DIVERSIFIED / OTHERS ──
    ("TITAN.NS", "Titan Company", "Consumer Durables", "NSE"),
    ("HAVELLS.NS", "Havells India", "Consumer Durables", "NSE"),
    ("VOLTAS.NS", "Voltas", "Consumer Durables", "NSE"),
    ("WHIRLPOOL.NS", "Whirlpool India", "Consumer Durables", "NSE"),
    ("CROMPTON.NS", "Crompton Greaves", "Consumer Durables", "NSE"),
    ("GRASIM.NS", "Grasim Industries", "Diversified", "NSE"),
    ("TRENT.NS", "Trent (Westside)", "Retail", "NSE"),
    ("DMART.NS", "Avenue Supermarts", "Retail", "NSE"),
    ("PAGEIND.NS", "Page Industries", "Textiles", "NSE"),
    ("INDIGO.NS", "InterGlobe Aviation", "Aviation", "NSE"),
    ("IRCTC.NS", "IRCTC", "Travel & Tourism", "NSE"),
    ("ZOMATO.NS", "Zomato", "Internet", "NSE"),
    ("PAYTM.NS", "One97 Communications", "Fintech", "NSE"),
    ("NYKAA.NS", "Nykaa", "E-Commerce", "NSE"),
    ("POLICYBZR.NS", "PB Fintech", "Fintech", "NSE"),
    ("DIXON.NS", "Dixon Technologies", "Electronics", "NSE"),
    ("KAYNES.NS", "Kaynes Technology", "Electronics", "NSE"),
    ("JIOFIN.NS", "Jio Financial Services", "Financial Services", "NSE"),

    # ── MORE LARGE / MID CAPS ──
    ("HINDPETRO.NS", "Hindustan Petroleum", "Oil & Gas", "NSE"),
    ("PETRONET.NS", "Petronet LNG", "Oil & Gas", "NSE"),
    ("IGL.NS", "Indraprastha Gas", "Oil & Gas", "NSE"),
    ("MGL.NS", "Mahanagar Gas", "Oil & Gas", "NSE"),
    ("PIIND.NS", "PI Industries", "Chemicals", "NSE"),
    ("ASTRAL.NS", "Astral", "Building Materials", "NSE"),
    ("POLYCAB.NS", "Polycab India", "Cables", "NSE"),
    ("KEI.NS", "KEI Industries", "Cables", "NSE"),
    ("SONACOMS.NS", "Sona BLW Precision", "Auto Ancillary", "NSE"),
    ("MOTHERSON.NS", "Samvardhana Motherson", "Auto Ancillary", "NSE"),
    ("BALKRISIND.NS", "Balkrishna Industries", "Auto Ancillary", "NSE"),
    ("EXIDEIND.NS", "Exide Industries", "Auto Ancillary", "NSE"),
    ("BOSCHLTD.NS", "Bosch", "Auto Ancillary", "NSE"),
    ("MFSL.NS", "Max Financial Services", "Insurance", "NSE"),
    ("SBICARD.NS", "SBI Cards", "Financial Services", "NSE"),
    ("CANFINHOME.NS", "Can Fin Homes", "NBFC", "NSE"),
    ("MANAPPURAM.NS", "Manappuram Finance", "NBFC", "NSE"),
    ("LICI.NS", "LIC of India", "Insurance", "NSE"),
    ("OFSS.NS", "Oracle Financial Services", "IT", "NSE"),
    ("TATAELXSI.NS", "Tata Elxsi", "IT", "NSE"),
    ("HAPPSTMNDS.NS", "Happiest Minds", "IT", "NSE"),
    ("NAUKRI.NS", "Info Edge", "Internet", "NSE"),
    ("INDIAMART.NS", "IndiaMART", "Internet", "NSE"),
    ("MAPMYINDIA.NS", "MapMyIndia", "IT", "NSE"),
    ("SYNGENE.NS", "Syngene International", "Pharma", "NSE"),
    ("GLENMARK.NS", "Glenmark Pharma", "Pharma", "NSE"),
    ("IPCALAB.NS", "IPCA Labs", "Pharma", "NSE"),
    ("ALKEM.NS", "Alkem Labs", "Pharma", "NSE"),
    ("LAURUSLABS.NS", "Laurus Labs", "Pharma", "NSE"),
    ("INDIANB.NS", "Indian Bank", "Banking", "NSE"),
    ("CANBK.NS", "Canara Bank", "Banking", "NSE"),
    ("UNIONBANK.NS", "Union Bank", "Banking", "NSE"),
    ("CGPOWER.NS", "CG Power", "Capital Goods", "NSE"),
    ("TIINDIA.NS", "Tube Investments", "Engineering", "NSE"),
    ("THERMAX.NS", "Thermax", "Capital Goods", "NSE"),
    ("APLAPOLLO.NS", "APL Apollo Tubes", "Building Materials", "NSE"),
    ("SUPREMEIND.NS", "Supreme Industries", "Building Materials", "NSE"),
    ("COCHINSHIP.NS", "Cochin Shipyard", "Defence", "NSE"),
    ("MAZAGONDOCK.NS", "Mazagon Dock", "Defence", "NSE"),
    ("GRSE.NS", "Garden Reach Shipbuilders", "Defence", "NSE"),
    ("BDL.NS", "Bharat Dynamics", "Defence", "NSE"),
    ("SOLARINDS.NS", "Solar Industries", "Defence", "NSE"),
    ("PARAS.NS", "Paras Defence", "Defence", "NSE"),
    ("DATAPATTNS.NS", "Data Patterns", "Defence", "NSE"),
    ("NHPC.NS", "NHPC", "Power", "NSE"),
    ("SJVN.NS", "SJVN", "Power", "NSE"),
    ("JSWENERGY.NS", "JSW Energy", "Power", "NSE"),
    ("TORNTPOWER.NS", "Torrent Power", "Power", "NSE"),
    ("CESC.NS", "CESC", "Power", "NSE"),
]


# ═══════════════════════════════════════════════════════════════
# NSE STOCK UNIVERSE
# ═══════════════════════════════════════════════════════════════

_cached_universe = None
_universe_cache_time = None


def _fetch_nse_equity_list():
    """Download the official NSE equity list CSV."""
    urls = [
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://www1.nseindia.com/content/equities/EQUITY_L.csv",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=NSE_HEADERS, timeout=15)
            if resp.status_code == 200:
                df = pd.read_csv(io.StringIO(resp.text))
                stocks = []
                for _, row in df.iterrows():
                    symbol = str(row.get("SYMBOL", "")).strip()
                    name = str(row.get("NAME OF COMPANY", symbol)).strip()
                    sector = str(row.get("INDUSTRY", "Unknown")).strip()
                    if symbol and symbol != "nan":
                        stocks.append((f"{symbol}.NS", name, sector, "NSE"))
                if len(stocks) > 100:
                    logger.info(f"Fetched {len(stocks)} NSE stocks from {url}")
                    return stocks
        except Exception as e:
            logger.warning(f"Failed to fetch NSE list from {url}: {e}")
    return None


def get_stock_universe():
    """
    Return ALL NSE-listed stocks (dynamically fetched, cached for 24h).
    Falls back to curated list if dynamic fetch fails.
    """
    global _cached_universe, _universe_cache_time

    if _cached_universe and _universe_cache_time:
        if datetime.now() - _universe_cache_time < timedelta(hours=24):
            return _cached_universe

    # Try fetching from file cache first
    cache_file = os.path.join(CACHE_DIR, "nse_universe.json")
    if os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - mtime < timedelta(hours=24):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                _cached_universe = [tuple(s) for s in data]
                _universe_cache_time = datetime.now()
                logger.info(f"Loaded {len(_cached_universe)} stocks from cache")
                return _cached_universe
            except Exception:
                pass

    # Try dynamic fetch
    stocks = _fetch_nse_equity_list()
    if stocks:
        _cached_universe = stocks
        _universe_cache_time = datetime.now()
        try:
            with open(cache_file, "w") as f:
                json.dump(stocks, f)
        except Exception:
            pass
        return stocks

    # Fallback
    logger.warning("Using fallback stock list")
    _cached_universe = FALLBACK_STOCKS
    _universe_cache_time = datetime.now()
    return FALLBACK_STOCKS


# ═══════════════════════════════════════════════════════════════
# DATA FETCHING WITH CACHING
# ═══════════════════════════════════════════════════════════════

def _get_cache_path(symbol, period):
    safe_symbol = symbol.replace(".", "_").replace("&", "_")
    return os.path.join(CACHE_DIR, f"{safe_symbol}_{period}.parquet")


def fetch_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame | None:
    """
    Fetch daily OHLCV data for a given symbol with file caching.
    Returns None if data is insufficient or fetch fails.
    """
    cache_path = _get_cache_path(symbol, period)

    # Check cache (valid for 6 hours during market days)
    if os.path.exists(cache_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - mtime < timedelta(hours=6):
            try:
                df = pd.read_parquet(cache_path)
                if len(df) >= 100:
                    return df
            except Exception:
                pass

    # Fetch from yfinance
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        if df is None or df.empty or len(df) < 100:
            return None

        # Clean column names
        df.columns = [c.strip() for c in df.columns]

        # Ensure we have required columns
        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in df.columns:
                return None

        # Save to cache
        try:
            df.to_parquet(cache_path)
        except Exception:
            pass

        return df
    except Exception as e:
        logger.debug(f"Failed to fetch {symbol}: {e}")
        return None


def fetch_nifty_data(period: str = "2y") -> pd.DataFrame | None:
    """Fetch NIFTY 50 index data for relative strength calculations."""
    return fetch_ohlcv("^NSEI", period)


def fetch_multiple_stocks(symbols: list, period: str = "2y", max_workers: int = 10):
    """
    Fetch data for multiple stocks in parallel.
    Returns dict of {symbol: DataFrame}.
    """
    results = {}

    def _fetch_one(sym):
        return sym, fetch_ohlcv(sym, period)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, sym): sym for sym in symbols}
        for future in as_completed(futures):
            try:
                sym, df = future.result()
                if df is not None:
                    results[sym] = df
            except Exception as e:
                logger.debug(f"Parallel fetch error: {e}")

    return results


def passes_universe_filter(df: pd.DataFrame, min_price=10, min_avg_volume=50000) -> bool:
    """
    Check if stock passes basic universe filters:
    - Price >= min_price
    - Average daily volume >= min_avg_volume
    """
    if df is None or df.empty:
        return False
    try:
        latest_close = df["Close"].iloc[-1]
        avg_vol = df["Volume"].tail(20).mean()
        return latest_close >= min_price and avg_vol >= min_avg_volume
    except Exception:
        return False
