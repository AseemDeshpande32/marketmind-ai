"""
MarketMind AI — Chatbot Agent Service

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Frontend Chat UI                                               │
  │       ↓  POST /api/chat { "message": "..." }                   │
  │  routes/chat.py                                                 │
  │       ↓                                                         │
  │  services/chat_service.py  ←── THIS FILE                       │
  │       ↓  detect_intent()                                        │
  │       ├── "general"       → build_general_prompt → Ollama      │
  │       ├── "comparison"    → fetch_stock_info × 2               │
  │       │                     fetch_sentiment × 2                 │
  │       │                     build_comparison_prompt → Ollama    │
  │       ├── "portfolio"     → extract_portfolio_items            │
  │       │                     fetch_stock_info × N                │
  │       │                     build_portfolio_prompt → Ollama     │
  │       └── "stock_query"   → fetch_stock_info                   │
  │                              fetch_sentiment                    │
  │                              build_stock_query_prompt → Ollama  │
  │       ↓                                                         │
  │  Ollama REST (localhost:11434) — Gemma model                    │
  │       ↓                                                         │
  │  JSON response → Frontend                                       │
  └─────────────────────────────────────────────────────────────────┘
"""

import re
import json
import logging
import requests
from typing import Any, Dict, Generator, List

from services.market_service import market_service
from services.script_master_service import script_master_service
from services.sentiment_service import run_sentiment_pipeline
from services.fundamentals_service import fundamentals_service

logger = logging.getLogger(__name__)

# ── Ollama configuration ───────────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"          # Must match model pulled in Ollama; change if needed
OLLAMA_TIMEOUT = 120             # seconds — Gemma can be slow on first inference

# ── Common Indian blue-chip stock name → NSE symbol mapping ──────────────────
KNOWN_STOCKS: Dict[str, str] = {
    "tcs":                     "TCS",
    "tata consultancy":        "TCS",
    "infosys":                 "INFY",
    "infy":                    "INFY",
    "wipro":                   "WIPRO",
    "reliance":                "RELIANCE",
    "reliance industries":     "RELIANCE",
    "ril":                     "RELIANCE",
    "hdfc":                    "HDFCBANK",
    "hdfc bank":               "HDFCBANK",
    "icici":                   "ICICIBANK",
    "icici bank":              "ICICIBANK",
    "sbi":                     "SBIN",
    "state bank":              "SBIN",
    "axis bank":               "AXISBANK",
    "kotak":                   "KOTAKBANK",
    "kotak mahindra":          "KOTAKBANK",
    "bajaj finance":           "BAJFINANCE",
    "bajaj":                   "BAJFINANCE",
    "maruti":                  "MARUTI",
    "maruti suzuki":           "MARUTI",
    "hindustan unilever":      "HINDUNILVR",
    "hul":                     "HINDUNILVR",
    "itc":                     "ITC",
    "sun pharma":              "SUNPHARMA",
    "sun pharmaceutical":      "SUNPHARMA",
    "dr reddy":                "DRREDDY",
    "drreddys":                "DRREDDY",
    "ongc":                    "ONGC",
    "ntpc":                    "NTPC",
    "power grid":              "POWERGRID",
    "bharti airtel":           "BHARTIARTL",
    "airtel":                  "BHARTIARTL",
    "adani ports":             "ADANIPORTS",
    "adani green":             "ADANIGREEN",
    "adani green energy":      "ADANIGREEN",
    "adani enterprises":       "ADANIENT",
    "adani power":             "ADANIPOWER",
    "adani energy":            "ADANIENSOL",
    "larsen":                  "LT",
    "l&t":                     "LT",
    "asian paints":            "ASIANPAINT",
    "titan":                   "TITAN",
    "ultratech":               "ULTRACEMCO",
    "nestle":                  "NESTLEIND",
    "hcl":                     "HCLTECH",
    "hcl technologies":        "HCLTECH",
    "tech mahindra":           "TECHM",
    "techm":                   "TECHM",
    "ltim":                    "LTIM",
    "mphasis":                 "MPHASIS",
    "bajaj auto":              "BAJAJ-AUTO",
    "hero":                    "HEROMOTOCO",
    "hero motocorp":           "HEROMOTOCO",
    "tata motors":             "TATAMOTORS",
    "tata steel":              "TATASTEEL",
    "tata power":              "TATAPOWER",
    "coal india":              "COALINDIA",
    "bpcl":                    "BPCL",
    "ioc":                     "IOC",
    "indian oil":              "IOC",
    "pidilite":                "PIDILITIND",
    "havells":                 "HAVELLS",
    "siemens":                 "SIEMENS",
    "abfrl":                   "ABFRL",
    "britannia":               "BRITANNIA",
    "dabur":                   "DABUR",
    "godrej":                  "GODREJCP",
    "marico":                  "MARICO",
}

# Deterministic sector map to avoid LLM-based sector mislabeling.
KNOWN_SECTORS: Dict[str, str] = {
    "RELIANCE": "Energy",
    "ONGC": "Energy",
    "BPCL": "Energy",
    "IOC": "Energy",
    "COALINDIA": "Energy",
    "ADANIGREEN": "Energy",
    "ADANIPOWER": "Energy",
    "NTPC": "Utilities",
    "POWERGRID": "Utilities",
    "TCS": "Information Technology",
    "INFY": "Information Technology",
    "WIPRO": "Information Technology",
    "HCLTECH": "Information Technology",
    "TECHM": "Information Technology",
    "LTIM": "Information Technology",
    "MPHASIS": "Information Technology",
    "HDFCBANK": "Financial Services",
    "ICICIBANK": "Financial Services",
    "SBIN": "Financial Services",
    "AXISBANK": "Financial Services",
    "KOTAKBANK": "Financial Services",
    "BAJFINANCE": "Financial Services",
    "ASIANPAINT": "Consumer Goods",
    "HINDUNILVR": "Consumer Goods",
    "ITC": "Consumer Goods",
    "NESTLEIND": "Consumer Goods",
    "BRITANNIA": "Consumer Goods",
    "DABUR": "Consumer Goods",
    "GODREJCP": "Consumer Goods",
    "MARICO": "Consumer Goods",
    "MARUTI": "Automobile",
    "BAJAJ-AUTO": "Automobile",
    "HEROMOTOCO": "Automobile",
    "TATAMOTORS": "Automobile",
    "TATASTEEL": "Metals",
    "ULTRACEMCO": "Materials",
    "LT": "Industrials",
    "ADANIPORTS": "Industrials",
    "SIEMENS": "Industrials",
    "PIDILITIND": "Chemicals",
    "SUNPHARMA": "Healthcare",
    "DRREDDY": "Healthcare",
    "BHARTIARTL": "Telecommunication",
    "TITAN": "Consumer Discretionary",
    "HAVELLS": "Consumer Durables",
    "ABFRL": "Consumer Discretionary",
    "MRF": "Automobile",
}


def _get_sector_for_symbol(symbol: str, exchange_code: str = "N") -> str:
    # Manual map remains a deterministic override for known names.
    mapped = KNOWN_SECTORS.get(symbol.upper())
    if mapped:
        return mapped

    # Yahoo Finance classification for symbols not present in manual map.
    sector_data = fundamentals_service.get_sector_classification(symbol, exchange_code)
    if not sector_data.get("error") and sector_data.get("sector"):
        return str(sector_data.get("sector"))

    return "Unclassified"

# ── Intent detection patterns ─────────────────────────────────────────────────
_COMPARE_RE = [
    re.compile(r"\bcompare\b", re.IGNORECASE),
    re.compile(r"\bvs\.?\b",   re.IGNORECASE),
    re.compile(r"\bversus\b",  re.IGNORECASE),
    re.compile(r"\bbetter\b.{0,40}\bor\b", re.IGNORECASE),
    re.compile(r"\bdifference between\b",  re.IGNORECASE),
]

_PORTFOLIO_RE = [
    re.compile(r"\bportfolio\b",              re.IGNORECASE),
    re.compile(r"\bi (own|have|hold|bought)\b", re.IGNORECASE),
    re.compile(r"\bmy stocks?\b",             re.IGNORECASE),
    re.compile(r"\bmy holdings?\b",           re.IGNORECASE),
    re.compile(r"\bmy investments?\b",        re.IGNORECASE),
    re.compile(r"\b\d+\s*(shares?|units?)\s*(of)?\s+[A-Za-z]", re.IGNORECASE),
    # "TCS 5" or "TCS:5" or "TCS - 5" patterns
    re.compile(r"\b[A-Z]{2,10}\s*[:\-]\s*\d+\b"),
]

_STOCK_QUERY_RE = [
    re.compile(r"\bprice of\b",                              re.IGNORECASE),
    re.compile(r"\bstock (price|data|info|details|report)\b", re.IGNORECASE),
    re.compile(r"\bhow is\b.{0,25}\b(trading|stock|doing|performing)\b", re.IGNORECASE),
    re.compile(r"\btell me about\b",                         re.IGNORECASE),
    re.compile(r"\banalyze\b",                               re.IGNORECASE),
    re.compile(r"\bsentiment (of|for|on)\b",                 re.IGNORECASE),
    re.compile(r"\banalysis (of|for|on)\b",                  re.IGNORECASE),
    re.compile(r"\bwhat.{0,20}(price|trading at)\b",         re.IGNORECASE),
]

_SUGGESTION_RE = [
    re.compile(r"\bshould i invest\b",                       re.IGNORECASE),
    re.compile(r"\bwhat.*invest\b",                          re.IGNORECASE),
    re.compile(r"\bsuggest.*invest\b",                       re.IGNORECASE),
    re.compile(r"\bwhich stock.*buy\b",                      re.IGNORECASE),
    re.compile(r"\bbest stock(s)? to buy\b",                 re.IGNORECASE),
    re.compile(r"\binvestment advice\b",                     re.IGNORECASE),
    re.compile(r"\binvest.*rupees?\b",                       re.IGNORECASE),
    re.compile(r"\brupees?.*invest\b",                       re.IGNORECASE),
    re.compile(r"\bwhere.*invest\b",                         re.IGNORECASE),
    re.compile(r"\bhow.*invest\b",                           re.IGNORECASE),
    re.compile(r"\byears? old\b",                            re.IGNORECASE),
    re.compile(r"\bfor retirement\b",                        re.IGNORECASE),
    re.compile(r"\blong.?term invest\b",                     re.IGNORECASE),
    # "I have X to invest" / "I want to invest X" — lump sum intent
    re.compile(r"\bi have.{0,60}\bto invest\b",              re.IGNORECASE),
    re.compile(r"\bi (want|plan|wish|need).{0,30}\binvest\b", re.IGNORECASE),
    re.compile(r"\blump.?sum\b",                              re.IGNORECASE),
    re.compile(r"\bone.?time invest\b",                       re.IGNORECASE),
]


# ── Intent detection ───────────────────────────────────────────────────────────
def _detect_intent(message: str) -> str:
    """
    Classify user message into one of:
      'comparison' | 'portfolio' | 'suggestion' | 'stock_query' | 'general'
    """
    if any(p.search(message) for p in _COMPARE_RE):
        return "comparison"
    if any(p.search(message) for p in _SUGGESTION_RE):
        return "suggestion"
    if any(p.search(message) for p in _PORTFOLIO_RE):
        return "portfolio"
    if any(p.search(message) for p in _STOCK_QUERY_RE):
        return "stock_query"
    return "general"


# ── Symbol extraction ──────────────────────────────────────────────────────────
def _extract_symbols(message: str) -> List[str]:
    """
    Extract NSE stock symbols from a message.
    Tries KNOWN_STOCKS name-mapping first, then scans for raw uppercase tickers.
    Preserves insertion order and deduplicates.
    """
    found: List[str] = []
    seen: set = set()
    lower_msg = message.lower()

    # 1. Named lookup (longest-match first to handle "HDFC Bank" before "HDFC")
    for name_key in sorted(KNOWN_STOCKS, key=len, reverse=True):
        sym = KNOWN_STOCKS[name_key]
        if name_key in lower_msg and sym not in seen:
            found.append(sym)
            seen.add(sym)

    # 2. Raw uppercase tickers (e.g. "TCS", "HDFCBANK")
    for t in re.findall(r"\b([A-Z][A-Z0-9\-]{1,11})\b", message):
        if t not in seen and len(t) >= 2:
            found.append(t)
            seen.add(t)

    return found


def _resolve_single_symbol(message: str) -> str | None:
    """
    Resolve one symbol from natural-language text.
    Priority:
      1) Explicit mapping / uppercase ticker extraction
      2) ScripMaster fuzzy search with normalized query text
    """
    symbols = _extract_symbols(message)
    if symbols:
        return symbols[0]

    lower_msg = message.lower()
    normalized = re.sub(
        r"\b(what|whats|what's|teh|the|current|latest|price|stock|share|quote|of|for|is|tell|me|about|today|now|nse|bse|inr|pls|please)\b",
        " ",
        lower_msg,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return None

    # Try longest phrase first, then shorter trailing windows.
    candidates = [normalized]
    words = normalized.split()
    for size in (4, 3, 2):
        if len(words) >= size:
            candidates.append(" ".join(words[-size:]))

    # Add common singular/plural variants (energy/energies, industry/industries)
    variant_candidates: List[str] = []
    for q in list(candidates):
        if " energy" in q or q.endswith("energy"):
            variant_candidates.append(q.replace("energy", "energies"))
        if " energies" in q or q.endswith("energies"):
            variant_candidates.append(q.replace("energies", "energy"))
        if " industry" in q or q.endswith("industry"):
            variant_candidates.append(q.replace("industry", "industries"))
        if " industries" in q or q.endswith("industries"):
            variant_candidates.append(q.replace("industries", "industry"))
    candidates.extend(variant_candidates)

    seen = set()
    for q in candidates:
        if q in seen:
            continue
        seen.add(q)
        try:
            matches = script_master_service.search_stock(
                q,
                exchange="N",
                exchange_type="C",
                limit=1,
            )
            if matches:
                symbol = (matches[0].get("symbolRoot") or "").strip().upper()
                if symbol:
                    logger.info("[CHAT] Resolved symbol via scrip search: query='%s' -> %s", q, symbol)
                    return symbol
        except Exception as exc:
            logger.warning("[CHAT] Symbol resolve search failed for '%s': %s", q, exc)

    # Last fallback: search by meaningful tokens and pick a confident match.
    tokens = [t for t in re.findall(r"[A-Za-z]{4,}", normalized) if t.lower() not in {"stock", "share", "price", "listed"}]
    for tok in tokens:
        try:
            matches = script_master_service.search_stock(
                tok,
                exchange="N",
                exchange_type="C",
                limit=3,
            )
            if len(matches) == 1:
                symbol = (matches[0].get("symbolRoot") or "").strip().upper()
                if symbol:
                    logger.info("[CHAT] Resolved symbol via token fallback: token='%s' -> %s", tok, symbol)
                    return symbol
            if matches:
                first = matches[0]
                full_name = (first.get("fullName") or "").upper()
                symbol = (first.get("symbolRoot") or "").strip().upper()
                if symbol and tok.upper() in full_name:
                    logger.info("[CHAT] Resolved symbol via token ranked fallback: token='%s' -> %s", tok, symbol)
                    return symbol
        except Exception as exc:
            logger.warning("[CHAT] Token fallback search failed for '%s': %s", tok, exc)

    return None


def _is_price_only_query(message: str) -> bool:
    """
    Detect whether the user is asking only for a quick quote/price.
    """
    msg = message.lower()

    price_signals = [
        "price",
        "current price",
        "stock price",
        "quote",
        "trading at",
        "ltp",
    ]
    deep_analysis_signals = [
        "analyze",
        "analysis",
        "outlook",
        "risk",
        "sentiment",
        "fundamental",
        "technical",
        "compare",
        "portfolio",
        "should i buy",
    ]

    has_price_signal = any(s in msg for s in price_signals)
    wants_deep_analysis = any(s in msg for s in deep_analysis_signals)
    return has_price_signal and not wants_deep_analysis


def _is_basic_stock_fact_query(message: str) -> bool:
    """
    Detect simple stock fact queries that should return strict live snapshot output
    instead of long free-form model analysis.
    """
    msg = message.lower()
    basic_patterns = [
        r"\bwhat is\b.*\bstock\b",
        r"\babout\b.*\bstock\b",
        r"\blisted\b.*\bstock\b",
        r"\bstock\s+info\b",
        r"\bstock\s+details\b",
    ]
    deep_patterns = [
        r"\banaly(s|z)e\b",
        r"\bvaluation\b",
        r"\boutlook\b",
        r"\brisk\b",
        r"\bsentiment\b",
        r"\bcompare\b",
        r"\bportfolio\b",
    ]
    is_basic = any(re.search(p, msg, re.IGNORECASE) for p in basic_patterns)
    is_deep = any(re.search(p, msg, re.IGNORECASE) for p in deep_patterns)
    return is_basic and not is_deep


def _build_stock_snapshot_response(symbol: str, stock: Dict[str, Any]) -> str:
    """Build a deterministic stock snapshot response from live API-backed fields."""
    if stock.get("error"):
        return f"- {symbol}: Live data unavailable ({stock.get('error')})."

    sign = "+" if stock.get("changePercent", 0) >= 0 else ""
    lines = [
        f"- {symbol} current price: ₹{stock.get('price', 0):,.2f}",
        f"- Day change: {sign}{stock.get('changePercent', 0):.2f}% (₹{stock.get('change', 0):+.2f})",
        f"- Open/High/Low: ₹{stock.get('open', 0):,.2f} / ₹{stock.get('high', 0):,.2f} / ₹{stock.get('low', 0):,.2f}",
        f"- Volume: {stock.get('volume', 0):,}",
    ]

    if stock.get("pe_ratio") is not None:
        lines.append(f"- P/E: {stock.get('pe_ratio'):.2f}")
    if stock.get("eps") is not None:
        lines.append(f"- EPS: ₹{stock.get('eps'):.2f}")
    if stock.get("book_value") is not None:
        lines.append(f"- Book Value: ₹{stock.get('book_value'):.2f}")
    if stock.get("sector"):
        lines.append(f"- Sector: {stock.get('sector')}")

    lines.append("- Source: 5paisa live market data (+ Yahoo for fundamentals/sector where applicable)")
    return "\n".join(lines)


def _extract_portfolio_items(message: str) -> List[Dict[str, Any]]:
    """
    Parse portfolio items from messages such as:
      "I have 100 shares of reliance and 50 of tcs"
      "100 shares of reliance, 50 shares tcs, 100 Asian paints, 1 MRF"
      "TCS 5, Infosys 10, Reliance 3"
    Returns list of dicts: { symbol, name, qty }
    """
    qty_by_symbol: Dict[str, Dict[str, Any]] = {}

    def _resolve_symbol(raw_name: str) -> str:
        name_lower = raw_name.lower().strip()
        symbol = raw_name.upper().strip()
        for key in sorted(KNOWN_STOCKS, key=len, reverse=True):
            if key in name_lower:
                return KNOWN_STOCKS[key]
        return symbol

    def _add_item(raw_name: str, qty: int) -> None:
        clean_name = re.sub(r"\b(of|shares?|units?|and)\b", " ", raw_name, flags=re.IGNORECASE)
        clean_name = re.sub(r"\s+", " ", clean_name).strip(" ,.-")
        if qty <= 0 or not clean_name:
            return

        # Reject multi-word names that are too long
        words = clean_name.split()
        if len(words) > 3:
            logger.debug(f"[CHAT] Portfolio: skipping name with >3 words: {clean_name}")
            return

        symbol = _resolve_symbol(clean_name)
        known_symbols = set(KNOWN_STOCKS.values())
        
        # Accept if known stock symbol
        if symbol in known_symbols:
            if symbol in qty_by_symbol:
                qty_by_symbol[symbol]["qty"] += qty
                return
            qty_by_symbol[symbol] = {"symbol": symbol, "name": clean_name, "qty": qty}
            return

        # Accept if valid 2-10 char NSE symbol
        if re.match(r"^[A-Z][A-Z0-9\-]{0,9}$", symbol) and "-" not in symbol.lstrip("_"):
            if symbol in qty_by_symbol:
                qty_by_symbol[symbol]["qty"] += qty
                return
            qty_by_symbol[symbol] = {"symbol": symbol, "name": clean_name, "qty": qty}
            return

        logger.debug(f"[CHAT] Portfolio: rejecting invalid symbol: {symbol} from '{clean_name}'")

    # PATTERN: Non-greedy quantity-to-name matching
    # "(\d+)" - quantity (non-greedy)
    # "\s+(?:shares?|units?|of)?\s*" - separator with optional keywords
    # "([A-Za-z][A-Za-z0-9\s&\.\-]*?)" - stock name (non-greedy, minimal match)
    # "(?=\d|\s*$|[,;]|and|analyse)" - lookahead: next is digit, end, comma/semicolon, "and", or "analyse"
    pattern = re.compile(
        r"(\d+)\s+(?:shares?|units?|of)?\s*([A-Za-z][A-Za-z0-9\s&\.\-]*?)(?=\s*\d|\s*$|[,;]|and|analyse)",
        re.IGNORECASE,
    )

    for qty_str, name in pattern.findall(message):
        try:
            qty = int(qty_str)
            _add_item(name, qty)
        except ValueError:
            continue

    result = list(qty_by_symbol.values())
    logger.info(f"[CHAT] Portfolio extraction: extracted {len(result)} unique items from message")
    for item in result:
        logger.info(f"[CHAT]   - {item['symbol']}: {item['qty']} shares")
    return result


# ── Data-fetching helpers ──────────────────────────────────────────────────────
def _fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """
    Fetch current market snapshot + fundamentals for a symbol via the existing 5paisa pipeline.
    Returns a clean dict or an error dict if data is unavailable.
    """
    try:
        scrip_code = script_master_service.get_scrip_code(symbol, "N")
        exchange_code = "N"
        if not scrip_code:
            scrip_code = script_master_service.get_scrip_code(symbol, "B")
            exchange_code = "B"
        if not scrip_code:
            return {"symbol": symbol, "error": f"'{symbol}' not found in ScripMaster"}

        snap = market_service.get_market_snapshot(scrip_code, exchange_code, "C")
        formatted = market_service.format_stock_data(snap, scrip_code, exchange_code, "C")
        if not formatted:
            return {"symbol": symbol, "error": "No snapshot data returned"}

        formatted["symbol"] = symbol
        formatted["sector"] = _get_sector_for_symbol(symbol, exchange_code)
        
        # Fetch fundamentals from Yahoo Finance
        fundamentals = fundamentals_service.get_fundamentals(symbol, exchange_code)
        if not fundamentals.get("error"):
            # Add fundamental metrics to formatted data
            formatted["pe_ratio"] = fundamentals.get("pe_ratio")
            formatted["forward_pe"] = fundamentals.get("forward_pe")
            formatted["eps"] = fundamentals.get("eps")
            formatted["book_value"] = fundamentals.get("book_value")
            formatted["market_cap"] = fundamentals.get("market_cap")
            formatted["fundamentals_source"] = "Yahoo Finance"
        
        return formatted
    except Exception as exc:
        logger.warning("[CHAT] _fetch_stock_info(%s) failed: %s", symbol, exc)
        return {"symbol": symbol, "error": str(exc)}


def _fetch_sentiment(stock_name: str) -> Dict[str, Any]:
    """
    Run the FinBERT sentiment pipeline for a stock.
    Returns the sentiment summary dict.
    """
    try:
        return run_sentiment_pipeline(stock_name, stock_name)
    except Exception as exc:
        logger.warning("[CHAT] _fetch_sentiment(%s) failed: %s", stock_name, exc)
        return {
            "overall_sentiment": "Unknown",
            "sentiment_score":   0.0,
            "positive_percent":  0,
            "neutral_percent":   100,
            "negative_percent":  0,
            "articles_analyzed": 0,
            "error": str(exc),
        }


# ── Ollama integration ─────────────────────────────────────────────────────────
def _call_ollama(prompt: str) -> str:
    """
    Send a prompt to the locally running Ollama instance (stream=false).
    Raises RuntimeError on connectivity / timeout issues.
    """
    payload = {
        "model":   OLLAMA_MODEL,
        "prompt":  prompt,
        "stream":  False,
        "options": {
            "temperature": 0.7,
            "top_p":       0.9,
            "num_predict": 1200,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure it is running: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama request timed out. The model may still be loading — please retry."
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama error: {exc}") from exc


def _stream_ollama(prompt: str) -> Generator[str, None, None]:
    """
    Generator that yields text tokens from Ollama one-by-one using stream=True.
    Raises RuntimeError on connectivity / timeout issues.
    """
    payload = {
        "model":   OLLAMA_MODEL,
        "prompt":  prompt,
        "stream":  True,
        "options": {
            "temperature": 0.7,
            "top_p":       0.9,
            "num_predict": 600,
        },
    }
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=OLLAMA_TIMEOUT) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure it is running: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama request timed out. The model may still be loading — please retry."
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama error: {exc}") from exc


# ── Conversation history formatting ────────────────────────────────────────────────
def _format_history(history: List[Dict[str, str]]) -> str:
    """
    Format conversation history into a string for prompt injection.
    history format: [{"role": "user" | "assistant", "content": "..."}]
    Returns empty string if history is None or empty.
    """
    if not history:
        return ""
    
    lines = ["=== CONVERSATION HISTORY ==="]
    for exchange in history[-5:]:  # Keep last 5 exchanges
        role = exchange.get("role", "user")
        content = exchange.get("content", "")
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content[:200]}...")  # Truncate long responses
    lines.append("=== END HISTORY ===\n")
    return "\n".join(lines) + "\n\n"


# ── Prompt templates ───────────────────────────────────────────────────────────
def _prompt_general(message: str, history: List[Dict[str, str]] = None) -> str:
    history_str = _format_history(history)
    return (
        "You are MarketMind AI, an intelligent Indian stock market assistant "
        "specialising in NSE/BSE listed companies, financial concepts, and investment analysis.\n\n"
        f"{history_str}"
        "Answer the question below clearly and concisely using short bullet points where possible. "
        "Use examples from Indian markets (NSE/BSE, INR). "
        "Keep the total response under 200 words.\n\n"
        f"Question: {message}\n\n"
        "Answer:"
    )


def _prompt_comparison(
    sym_a: str, sym_b: str,
    stock_a: Dict, stock_b: Dict,
    sent_a: Dict, sent_b: Dict,
    history: List[Dict[str, str]] = None,
) -> str:
    def _block(sym: str, s: Dict, sent: Dict) -> str:
        if s.get("error"):
            return f"{sym}: Live data unavailable — {s['error']}"
        sign = "+" if s.get("changePercent", 0) >= 0 else ""
        
        # Format fundamentals if available
        fundamentals_str = ""
        if s.get("pe_ratio") is not None or s.get("eps") is not None or s.get("book_value") is not None:
            fundamentals_str = "  Fundamentals : "
            parts = []
            if s.get("pe_ratio") is not None:
                parts.append(f"P/E {s.get('pe_ratio'):.2f}")
            if s.get("eps") is not None:
                parts.append(f"EPS ₹{s.get('eps'):.2f}")
            if s.get("book_value") is not None:
                parts.append(f"BV ₹{s.get('book_value'):.2f}")
            fundamentals_str += " | ".join(parts)
            fundamentals_str += " (Yahoo Finance)\n"
        
        return (
            f"{sym}:\n"
            f"  Current Price : ₹{s.get('price', 0):>10,.2f}\n"
            f"  Day Change    : {sign}{s.get('changePercent', 0):.2f}%"
            f"  (₹{s.get('change', 0):+.2f})\n"
            f"  Open / High / Low: ₹{s.get('open', 0):,.2f} / "
            f"₹{s.get('high', 0):,.2f} / ₹{s.get('low', 0):,.2f}\n"
            f"{fundamentals_str}"
            f"  Volume        : {s.get('volume', 0):,}\n"
            f"  News Sentiment: {sent.get('overall_sentiment', 'N/A')} "
            f"(+{sent.get('positive_percent', 0):.0f}% positive / "
            f"{sent.get('negative_percent', 0):.0f}% negative, "
            f"{sent.get('articles_analyzed', 0)} articles)"
        )

    history_str = _format_history(history)
    return (
        "You are MarketMind AI, an expert Indian stock market analyst.\n\n"
        f"{history_str}"
        "Below is real-time market data and news sentiment for two NSE-listed stocks.\n\n"
        "=== LIVE MARKET DATA ===\n"
        f"{_block(sym_a, stock_a, sent_a)}\n\n"
        f"{_block(sym_b, stock_b, sent_b)}\n\n"
        "=== COMPARISON REPORT ===\n"
        "Use ONLY bullet points (• ). No paragraphs. Keep each section to 2-3 bullets max.\n\n"
        "**1. Price & Movement**\n"
        "• Compare current prices, day change %, and intraday range.\n\n"
        "**2. News Sentiment**\n"
        "• Compare news sentiment outlook and positive/negative split.\n\n"
        "**3. Financial Fundamentals**\n"
        "• Compare P/E ratio, EPS, book value using data provided + general knowledge of these companies.\n\n"
        "**4. Volume & Activity**\n"
        "• Compare trading volumes and what they signal about investor interest.\n\n"
        "**5. Verdict**\n"
        "• Which looks more attractive right now and one-line reason why.\n\n"
        "Be data-specific where possible. Total response under 300 words."
    )


def _prompt_portfolio(items: List[Dict], enriched: List[Dict], history: List[Dict[str, str]] = None) -> str:
    total = sum(i.get("total_value", 0) for i in enriched if not i.get("error"))
    valid_items = [i for i in enriched if not i.get("error")]

    if not valid_items:
        return (
            "You are MarketMind AI. Portfolio data is unavailable. "
            "Respond in 2 short bullets asking the user to retry with valid NSE/BSE symbols."
        )

    def _valuation_tag(pe: float | None) -> str:
        if pe is None:
            return "N/A"
        if pe >= 25:
            return "Expensive"
        if pe >= 18:
            return "Fair"
        return "Attractive"

    # Portfolio valuation summary
    weighted_pe_numerator = 0.0
    pe_weight_denom = 0.0
    for item in valid_items:
        val = float(item.get("total_value", 0) or 0)
        pe = item.get("pe_ratio")
        if pe is not None and val > 0:
            weighted_pe_numerator += float(pe) * val
            pe_weight_denom += val
    weighted_avg_pe = (weighted_pe_numerator / pe_weight_denom) if pe_weight_denom > 0 else None
    portfolio_valuation_tag = _valuation_tag(weighted_avg_pe)

    # Daily PnL snapshot
    today_pnl = 0.0
    for item in valid_items:
        today_pnl += float(item.get("change", 0) or 0) * float(item.get("qty", 0) or 0)

    # Best / worst performer by day return contribution
    ranked_by_day = sorted(
        valid_items,
        key=lambda i: float(i.get("change", 0) or 0) * float(i.get("qty", 0) or 0),
        reverse=True,
    )
    best_item = ranked_by_day[0]
    worst_item = ranked_by_day[-1]

    # Concentration & sector risk
    ranked_by_value = sorted(valid_items, key=lambda i: float(i.get("total_value", 0) or 0), reverse=True)
    largest_holding = ranked_by_value[0]
    largest_holding_pct = (float(largest_holding.get("total_value", 0) or 0) / total * 100) if total else 0.0

    sector_allocation: Dict[str, float] = {}
    for item in valid_items:
        sector = item.get("sector") or _get_sector_for_symbol(item.get("symbol", ""), "N")
        val = float(item.get("total_value", 0) or 0)
        sector_allocation[sector] = sector_allocation.get(sector, 0.0) + val
    top_sector, top_sector_value = max(sector_allocation.items(), key=lambda x: x[1])
    top_sector_pct = (top_sector_value / total * 100) if total else 0.0

    # Risk score out of 10: concentration + valuation driven
    risk_score = 3.0
    risk_score += min(3.0, max(0.0, (largest_holding_pct - 25.0) / 10.0))
    risk_score += min(2.5, max(0.0, (top_sector_pct - 35.0) / 10.0))
    if weighted_avg_pe is not None:
        risk_score += min(1.5, max(0.0, (weighted_avg_pe - 22.0) / 8.0))
    risk_score = round(min(10.0, max(1.0, risk_score)), 1)

    # Top holdings breakdown (top 4)
    top_holdings_lines: List[str] = []
    for item in ranked_by_value[:3]:
        wt = (float(item.get("total_value", 0) or 0) / total * 100) if total else 0.0
        holding_tag = _valuation_tag(item.get("pe_ratio"))
        top_holdings_lines.append(
            f"- {item.get('symbol')} - {wt:.1f}% - {holding_tag}"
        )
    top_holdings_block = "\n".join(top_holdings_lines)

    others_items = ranked_by_value[3:]
    others_value = sum(float(item.get("total_value", 0) or 0) for item in others_items)
    others_pct = (others_value / total * 100) if total else 0.0
    others_count = len(others_items)
    others_symbols = ", ".join(item.get("symbol") for item in others_items[:6])
    if others_count > 6:
        others_symbols += ", ..."
    if not others_symbols:
        others_symbols = "None"

    # Smart recommendations (deterministic hints)
    recommendations: List[str] = []
    if largest_holding_pct >= 35:
        recommendations.append(f"Trim overweight {largest_holding.get('symbol')} ({largest_holding_pct:.1f}% allocation)")
    if top_sector_pct >= 50:
        recommendations.append(f"Add a defensive non-{top_sector} sector to reduce concentration")
    if weighted_avg_pe is not None and weighted_avg_pe >= 25:
        recommendations.append("Rebalance into fair-value names; portfolio valuation is elevated")
    if not recommendations:
        recommendations.append("Maintain allocation and rebalance monthly")
    recommendations = recommendations[:3]
    recommendations_block = "\n".join(f"- {r}" for r in recommendations)

    gain_loss_label = "Gain" if today_pnl >= 0 else "Loss"
    history_str = _format_history(history)
    weighted_pe_line = f"Weighted Avg P/E: {weighted_avg_pe:.2f}" if weighted_avg_pe is not None else "Weighted Avg P/E: N/A"

    return (
        "You are MarketMind AI, an expert Indian portfolio analyst.\n\n"
        f"{history_str}"
        "User wants a structured but insightful portfolio analysis. Follow EXACTLY this format.\n"
        "Use only bullets and keep it readable, but include enough reasoning to make decisions.\n"
        "CRITICAL RULES: Only mention stocks that are actually present in the user's portfolio holdings below.\n"
        "Do NOT introduce new company names, tickers, or example holdings that are not part of the provided list.\n"
        "IMPORTANT: The following input metrics are INTERNAL CONTEXT only.\n"
        "Do NOT print them verbatim. Do NOT include any heading like PRECOMPUTED METRICS.\n"
        "Only use them to produce the final 5 sections.\n\n"
        "[INTERNAL_INPUT_METRICS]\n"
        f"Total Value: ₹{total:,.2f}\n"
        f"Today's Gain/Loss: {gain_loss_label} ₹{abs(today_pnl):,.2f}\n"
        f"Best Performer: {best_item.get('symbol')} ({best_item.get('changePercent', 0):+.2f}%)\n"
        f"Worst Performer: {worst_item.get('symbol')} ({worst_item.get('changePercent', 0):+.2f}%)\n"
        f"{weighted_pe_line}\n"
        f"Portfolio Valuation Tag: {portfolio_valuation_tag}\n"
        f"Largest Holding: {largest_holding.get('symbol')} ({largest_holding_pct:.1f}%)\n"
        f"Sector Concentration: {top_sector} ({top_sector_pct:.1f}%)\n"
        f"Risk Score: {risk_score}/10\n"
        f"Top Holdings:\n{top_holdings_block}\n"
        f"Recommendations:\n{recommendations_block}\n"
        "[/INTERNAL_INPUT_METRICS]\n\n"
        "=== REQUIRED RESPONSE FORMAT ===\n"
        "1. Portfolio Summary\n"
        "- Total Value\n"
        "- Best Performing Stock Today\n"
        "- Worst Performing Stock Today\n"
        "- Average Portfolio P/E\n\n"
        "2. Valuation Assessment\n"
        "- Keep this section short: 2-3 bullets max\n"
        "- Summarize expensive / fair / attractive holdings\n"
        "- Use the provided tags only; do not invent extra holdings\n\n"
        "3. Diversification\n"
        "- Mention sector spread\n"
        "- Mention concentration / over-exposure risk\n"
        "- Keep this section short: 2-3 bullets max\n\n"
        "4. Breakdown\n"
        "- Show ONLY the top 3 holdings\n"
        "- Format: SYMBOL - WEIGHT% - TAG - short reason\n"
        "- Then show Others as one aggregated bucket for all remaining holdings\n"
        f"- Others: {others_pct:.1f}% across {others_count} holdings\n"
        f"- Holdings included: {others_symbols}\n"
        "- Mention whether Others increases or reduces concentration risk\n\n"
        "5. Strategic Recommendations\n"
        "- 3 actionable bullets\n"
        "- Recommendations must reference only existing holdings or generic sectors.\n"
        "- Do not add or suggest a specific company ticker that is not already in the portfolio.\n"
        "- Include one concrete rebalance target split using only current holdings.\n\n"
        "Strictly follow section names and order above. Keep decision-focused and moderately detailed.\n"
        "Never output internal tags/blocks such as INTERNAL_INPUT_METRICS or PRECOMPUTED METRICS."
    )


def _prompt_stock_query(symbol: str, stock: Dict, sentiment: Dict, history: List[Dict[str, str]] = None) -> str:
    if stock.get("error"):
        return _prompt_general(f"Tell me about {symbol} stock listed on NSE India.", history)

    sign = "+" if stock.get("changePercent", 0) >= 0 else ""
    
    # Build fundamentals section if available
    fundamentals_section = ""
    if stock.get("pe_ratio") is not None or stock.get("eps") is not None or stock.get("book_value") is not None:
        fundamentals_section = "=== FUNDAMENTAL METRICS ===\n"
        if stock.get("pe_ratio") is not None:
            fundamentals_section += f"P/E Ratio      : {stock.get('pe_ratio'):.2f}\n"
        if stock.get("forward_pe") is not None:
            fundamentals_section += f"Forward P/E    : {stock.get('forward_pe'):.2f}\n"
        if stock.get("eps") is not None:
            fundamentals_section += f"EPS            : ₹{stock.get('eps'):.2f}\n"
        if stock.get("book_value") is not None:
            fundamentals_section += f"Book Value     : ₹{stock.get('book_value'):.2f}\n"
        if stock.get("market_cap") is not None:
            market_cap = stock.get('market_cap')
            if market_cap >= 1e12:
                cap_str = f"₹{market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                cap_str = f"₹{market_cap/1e9:.2f}B"
            else:
                cap_str = f"₹{market_cap:,.0f}"
            fundamentals_section += f"Market Cap     : {cap_str}\n"
        fundamentals_section += "Source         : Yahoo Finance\n\n"
    
    history_str = _format_history(history)
    return (
        "You are MarketMind AI, an expert Indian stock market analyst.\n\n"
        f"{history_str}"
        f"Below is real-time data and FinBERT news sentiment for {symbol} (NSE).\n\n"
        "CRITICAL: Use only the exact resolved company symbol/name shown above.\n"
        "Do NOT mention former names, renamed entities, acquisitions, or company history unless the user explicitly asks for it.\n"
        "Do NOT guess background facts. Rely only on the live market data and fundamentals shown below.\n\n"
        "=== LIVE MARKET DATA ===\n"
        f"Symbol        : {symbol}\n"
        f"Current Price : ₹{stock.get('price', 0):,.2f}\n"
        f"Day Change    : {sign}{stock.get('changePercent', 0):.2f}%"
        f"  (₹{stock.get('change', 0):+.2f})\n"
        f"Open          : ₹{stock.get('open', 0):,.2f}\n"
        f"High / Low    : ₹{stock.get('high', 0):,.2f} / ₹{stock.get('low', 0):,.2f}\n"
        f"Volume        : {stock.get('volume', 0):,}\n\n"
        f"{fundamentals_section}"
        "=== NEWS SENTIMENT ===\n"
        f"Overall       : {sentiment.get('overall_sentiment', 'N/A')}\n"
        f"Breakdown     : +{sentiment.get('positive_percent', 0):.0f}% Positive"
        f"  |  {sentiment.get('neutral_percent', 0):.0f}% Neutral"
        f"  |  {sentiment.get('negative_percent', 0):.0f}% Negative\n"
        f"Articles      : {sentiment.get('articles_analyzed', 0)} analysed\n\n"
        "=== STOCK ANALYSIS ===\n"
        "Use ONLY bullet points (• ). No paragraphs. 2-3 bullets per section max.\n\n"
        "**1. Market Status**\n"
        "• Current price, day change %, and what the movement signals.\n\n"
        "**2. Fundamentals Health**\n"
        "• P/E valuation (cheap/fair/expensive), EPS trend, book value status using data provided.\n\n"
        "**3. News Sentiment**\n"
        "• FinBERT score, positive/negative split, investor confidence summary.\n\n"
        "**4. Technical Snapshot**\n"
        "• High/low range, volume vs typical, any notable intraday pattern.\n\n"
        "**5. Short-term Outlook**\n"
        "• Balanced 1-2 bullet view: bullish factors vs risks.\n\n"
        "**6. Key Risks**\n"
        "• 2 main risks investors should watch.\n\n"
        "Be data-specific. Reference actual numbers. Total response under 250 words."
    )


def _prompt_price_quote(symbol: str, stock: Dict, history: List[Dict[str, str]] = None) -> str:
    """
    Short prompt for users asking only the current price/quote.
    """
    if stock.get("error"):
        return _prompt_general(f"Tell me the current price of {symbol} on NSE.", history)

    sign = "+" if stock.get("changePercent", 0) >= 0 else ""
    history_str = _format_history(history)
    return (
        "You are MarketMind AI. User asked only for a quick stock quote.\n\n"
        f"{history_str}"
        "Respond in 2-4 short bullet points only. Do not give full analysis sections.\n"
        "Do not add long recommendations, risk commentary, or deep insights unless user asks.\n\n"
        "CRITICAL: Use only the exact symbol shown below. Do NOT mention former names, company history, or alternative entities.\n\n"
        "=== QUOTE DATA ===\n"
        f"Symbol: {symbol}\n"
        f"Current Price: ₹{stock.get('price', 0):,.2f}\n"
        f"Day Change: {sign}{stock.get('changePercent', 0):.2f}% (₹{stock.get('change', 0):+.2f})\n"
        f"Open: ₹{stock.get('open', 0):,.2f}\n"
        f"High: ₹{stock.get('high', 0):,.2f}\n"
        f"Low: ₹{stock.get('low', 0):,.2f}\n"
        f"Volume: {stock.get('volume', 0):,}\n\n"
        "Return concise quote only."
    )


def _detect_investment_type(message: str) -> str:
    """Returns 'lump_sum', 'sip', or 'unknown' based on explicit keywords in the message."""
    msg_lower = message.lower()
    lump_keywords = ["lump sum", "lumpsum", "lump-sum", "one time", "one-time", "onetime",
                     "i have", "i want to invest", "to invest"]
    sip_keywords  = ["sip", "monthly", "per month", "every month", "recurring"]
    is_sip  = any(k in msg_lower for k in sip_keywords)
    is_lump = any(k in msg_lower for k in lump_keywords)
    if is_sip and not is_lump:
        return "sip"
    if is_lump and not is_sip:
        return "lump_sum"
    if is_lump and is_sip:
        return "lump_sum"   # explicit lump sum wins
    return "unknown"


def _prompt_suggestion(message: str, history: List[Dict[str, str]] = None) -> str:
    history_str = _format_history(history)
    inv_type = _detect_investment_type(message)

    if inv_type == "lump_sum":
        inv_fact = "CONFIRMED FACT: The user is making a ONE-TIME LUMP SUM investment. Do NOT treat it as SIP or monthly. Do NOT mention any monthly SIP amount."
    elif inv_type == "sip":
        inv_fact = "CONFIRMED FACT: The user is making a recurring monthly SIP investment."
    else:
        inv_fact = "Investment type not explicitly stated — ask the user or treat the amount as lump sum by default."

    return (
        "You are MarketMind AI, an expert Indian investment advisor.\n\n"
        f"{history_str}"
        f"⚠ {inv_fact}\n\n"
        "STRICT RULES — obey without exception:\n"
        "• Do NOT invent a monthly income or salary unless the user explicitly mentioned it.\n"
        "• Do NOT assume any age unless the user mentioned it.\n"
        "• If the investment is lump sum, never suggest a 'SIP amount per month' — suggest how to deploy the lump sum instead.\n\n"
        f"User's query: {message}\n\n"
        "=== INVESTMENT RECOMMENDATION ===\n"
        "Use ONLY bullet points (• ). No paragraphs. 2-3 bullets per section max.\n\n"
        "**1. Investor Profile**\n"
        "• Investment amount and type (lump sum or SIP), age if mentioned, inferred risk profile. Only include income if the user stated it — do NOT fabricate it.\n\n"
        "**2. Recommended Allocation**\n"
        "• % split: large-cap equity, mid-cap, debt/bonds, gold — tailored to their risk profile.\n\n"
        "**3. Specific Picks**\n"
        "• 3-4 specific NSE stocks or index funds with one-line reason each.\n\n"
        "**4. Investment Strategy**\n"
        "• If lump sum: suggest how to deploy it (staggered entry / all-at-once), time horizon, when to review.\n"
        "• If SIP: monthly amount, time horizon, when to review.\n\n"
        "**5. Key Caution**\n"
        "• 2 risks to be aware of before investing.\n\n"
        "Total response under 280 words. All amounts in INR. Note this is educational, not SEBI-registered advice."
    )


# ── Main agent entry point ─────────────────────────────────────────────────────
def process_chat(message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Main agent function called by the /api/chat route.

    1. Detects user intent.
    2. Fetches live data (stock price, sentiment) when required.
    3. Builds a structured prompt.
    4. Calls Ollama (Gemma) and returns the response.

    Args:
        message: User's current message
        history: Conversation history [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        {
          "response": str,          # LLM-generated text
          "intent":   str,          # detected intent
          "data":     dict | None,  # live market data used (optional)
        }
    Raises RuntimeError when Ollama is unreachable.
    """
    intent = _detect_intent(message)
    logger.info("[CHAT] intent=%s  msg=%.80s…", intent, message)

    # If a general query clearly references a stock, force stock_query path
    # so the reply is grounded in live API data instead of generic model text.
    if intent == "general":
        forced_symbol = _resolve_single_symbol(message)
        if forced_symbol:
            intent = "stock_query"

    # ── Stock comparison ─────────────────────────────────────────────────────
    if intent == "comparison":
        symbols = _extract_symbols(message)
        if len(symbols) < 2:
            # Not enough symbols — fall back to a general LLM answer
            return {
                "response": _call_ollama(_prompt_general(message, history)),
                "intent":   "comparison_fallback",
                "data":     None,
            }

        sym_a, sym_b = symbols[0], symbols[1]
        logger.info("[CHAT] Comparing %s vs %s", sym_a, sym_b)

        stock_a = _fetch_stock_info(sym_a)
        stock_b = _fetch_stock_info(sym_b)
        sent_a  = _fetch_sentiment(sym_a)
        sent_b  = _fetch_sentiment(sym_b)

        prompt   = _prompt_comparison(sym_a, sym_b, stock_a, stock_b, sent_a, sent_b, history)
        response = _call_ollama(prompt)

        return {
            "response": response,
            "intent":   "comparison",
            "data": {
                sym_a: {"stock": stock_a, "sentiment": sent_a},
                sym_b: {"stock": stock_b, "sentiment": sent_b},
            },
        }

    # ── Portfolio analysis ───────────────────────────────────────────────────
    if intent == "portfolio":
        items = _extract_portfolio_items(message)

        if not items:
            # Fallback: grab any symbols, assume qty = 1
            symbols = _extract_symbols(message)
            items = [{"symbol": s, "name": s, "qty": 1} for s in symbols[:10]]

        if not items:
            return {
                "response": _call_ollama(_prompt_general(message, history)),
                "intent":   "portfolio_fallback",
                "data":     None,
            }

        logger.info("[CHAT] Portfolio items: %s", items)

        enriched = []
        for item in items:
            info  = _fetch_stock_info(item["symbol"])
            entry = {**item, **info}
            if not info.get("error"):
                entry["total_value"] = round(info["price"] * item["qty"], 2)
            enriched.append(entry)

        prompt   = _prompt_portfolio(items, enriched, history)
        response = _call_ollama(prompt)

        return {
            "response": response,
            "intent":   "portfolio",
            "data":     enriched,
        }

    # ── Single stock query ───────────────────────────────────────────────────
    if intent == "stock_query":
        symbol = _resolve_single_symbol(message)
        if not symbol:
            return {
                "response": _call_ollama(_prompt_general(message, history)),
                "intent":   "general",
                "data":     None,
            }

        stock     = _fetch_stock_info(symbol)
        sentiment = _fetch_sentiment(symbol)
        if _is_price_only_query(message) or _is_basic_stock_fact_query(message):
            response = _build_stock_snapshot_response(symbol, stock)
        else:
            prompt = _prompt_stock_query(symbol, stock, sentiment, history)
            response = _call_ollama(prompt)

        return {
            "response": response,
            "intent":   "stock_query",
            "data":     {"stock": stock, "sentiment": sentiment},
        }

    # ── Investment suggestion ─────────────────────────────────────────────────
    if intent == "suggestion":
        return {
            "response": _call_ollama(_prompt_suggestion(message, history)),
            "intent":   "suggestion",
            "data":     None,
        }

    # ── General finance Q&A / fallback ──────────────────────────────────────
    return {
        "response": _call_ollama(_prompt_general(message, history)),
        "intent":   "general",
        "data":     None,
    }


# ── Streaming agent entry point ────────────────────────────────────────────────
def stream_process_chat(message: str, history: List[Dict[str, str]] = None) -> Generator[Dict, None, None]:
    """
    Streaming version of process_chat.

    Args:
        message: User's current message
        history: Conversation history [{"role": "user"|"assistant", "content": "..."}]

    Yields SSE-compatible dicts in order:
      {"type": "meta",  "intent": str, "data": dict|None}  — once, before tokens
      {"type": "token", "text": str}                        — one per LLM token
      {"type": "done"}                                      — signals completion
    """
    intent = _detect_intent(message)
    logger.info("[CHAT STREAM] intent=%s  msg=%.80s…", intent, message)

    # If a general query clearly references a stock, force stock_query path
    # so streaming also stays grounded in live API data.
    if intent == "general":
        forced_symbol = _resolve_single_symbol(message)
        if forced_symbol:
            intent = "stock_query"

    # ── Stock comparison ─────────────────────────────────────────────────────
    if intent == "comparison":
        symbols = _extract_symbols(message)
        if len(symbols) < 2:
            yield {"type": "meta", "intent": "comparison_fallback", "data": None}
            for token in _stream_ollama(_prompt_general(message, history)):
                yield {"type": "token", "text": token}
            yield {"type": "done"}
            return

        sym_a, sym_b = symbols[0], symbols[1]
        logger.info("[CHAT STREAM] Comparing %s vs %s", sym_a, sym_b)

        stock_a = _fetch_stock_info(sym_a)
        stock_b = _fetch_stock_info(sym_b)
        sent_a  = _fetch_sentiment(sym_a)
        sent_b  = _fetch_sentiment(sym_b)

        data = {
            sym_a: {"stock": stock_a, "sentiment": sent_a},
            sym_b: {"stock": stock_b, "sentiment": sent_b},
        }
        yield {"type": "meta", "intent": "comparison", "data": data}
        for token in _stream_ollama(_prompt_comparison(sym_a, sym_b, stock_a, stock_b, sent_a, sent_b, history)):
            yield {"type": "token", "text": token}
        yield {"type": "done"}
        return

    # ── Portfolio analysis ───────────────────────────────────────────────────
    if intent == "portfolio":
        items = _extract_portfolio_items(message)
        if not items:
            symbols = _extract_symbols(message)
            items = [{"symbol": s, "name": s, "qty": 1} for s in symbols[:10]]

        if not items:
            yield {"type": "meta", "intent": "portfolio_fallback", "data": None}
            for token in _stream_ollama(_prompt_general(message, history)):
                yield {"type": "token", "text": token}
            yield {"type": "done"}
            return

        enriched = []
        for item in items:
            info  = _fetch_stock_info(item["symbol"])
            entry = {**item, **info}
            if not info.get("error"):
                entry["total_value"] = round(info["price"] * item["qty"], 2)
            enriched.append(entry)

        yield {"type": "meta", "intent": "portfolio", "data": enriched}
        for token in _stream_ollama(_prompt_portfolio(items, enriched, history)):
            yield {"type": "token", "text": token}
        yield {"type": "done"}
        return

    # ── Single stock query ───────────────────────────────────────────────────
    if intent == "stock_query":
        symbol = _resolve_single_symbol(message)
        if not symbol:
            yield {"type": "meta", "intent": "general", "data": None}
            for token in _stream_ollama(_prompt_general(message, history)):
                yield {"type": "token", "text": token}
            yield {"type": "done"}
            return

        stock     = _fetch_stock_info(symbol)
        sentiment = _fetch_sentiment(symbol)

        yield {"type": "meta", "intent": "stock_query", "data": {"stock": stock, "sentiment": sentiment}}
        if _is_price_only_query(message) or _is_basic_stock_fact_query(message):
            yield {"type": "token", "text": _build_stock_snapshot_response(symbol, stock)}
        else:
            stream_prompt = _prompt_stock_query(symbol, stock, sentiment, history)
            for token in _stream_ollama(stream_prompt):
                yield {"type": "token", "text": token}
        yield {"type": "done"}
        return

    # ── Investment suggestion ─────────────────────────────────────────────────
    if intent == "suggestion":
        yield {"type": "meta", "intent": "suggestion", "data": None}
        for token in _stream_ollama(_prompt_suggestion(message, history)):
            yield {"type": "token", "text": token}
        yield {"type": "done"}
        return

    # ── General finance Q&A / fallback ──────────────────────────────────────
    yield {"type": "meta", "intent": "general", "data": None}
    for token in _stream_ollama(_prompt_general(message, history)):
        yield {"type": "token", "text": token}
    yield {"type": "done"}

