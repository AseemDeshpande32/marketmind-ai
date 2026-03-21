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
]


# ── Intent detection ───────────────────────────────────────────────────────────
def _detect_intent(message: str) -> str:
    """
    Classify user message into one of:
      'comparison' | 'portfolio' | 'suggestion' | 'stock_query' | 'general'
    """
    if any(p.search(message) for p in _COMPARE_RE):
        return "comparison"
    if any(p.search(message) for p in _PORTFOLIO_RE):
        return "portfolio"
    if any(p.search(message) for p in _SUGGESTION_RE):
        return "suggestion"
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


def _extract_portfolio_items(message: str) -> List[Dict[str, Any]]:
    """
    Parse portfolio items from messages such as:
      "TCS 5, Infosys 10, Reliance 3"
      "TCS:5 INFY:10 RELIANCE:3"
      "I have TCS - 5 shares and Infosys - 10 shares"
      "10 shares of MRF, 15 shares of Reliance, 10 shares of TCS"
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

        # Reject multi-word names that are too long (likely extracted junk)
        words = clean_name.split()
        if len(words) > 3:
            logger.debug(f"[CHAT] Portfolio: skipping name with >3 words: {clean_name}")
            return

        symbol = _resolve_symbol(clean_name)

        # STRICT VALIDATION: Only accept known stocks or valid 2-10 char uppercase symbols
        known_symbols = set(KNOWN_STOCKS.values())
        
        # Accept if it's a known stock symbol
        if symbol in known_symbols:
            if symbol in qty_by_symbol:
                qty_by_symbol[symbol]["qty"] += qty
                return
            qty_by_symbol[symbol] = {
                "symbol": symbol,
                "name": clean_name,
                "qty": qty,
            }
            return

        # Accept if it's a plausible NSE symbol (2-10 uppercase letters, hyphens, no lowercase)
        if re.match(r"^[A-Z][A-Z0-9\-]{0,9}$", symbol) and "-" not in symbol.lstrip("_"):
            if symbol in qty_by_symbol:
                qty_by_symbol[symbol]["qty"] += qty
                return
            qty_by_symbol[symbol] = {
                "symbol": symbol,
                "name": clean_name,
                "qty": qty,
            }
            return

        # Otherwise reject as junk
        logger.debug(f"[CHAT] Portfolio: rejecting invalid symbol: {symbol} from '{clean_name}'")

    # Pattern 1: name then quantity ("TCS 10", "Reliance:15", "Infosys - 5 shares")
    # Must have quantity directly after name, optional separator, optional quantity keyword
    name_first_pat = re.compile(
        r"\b([A-Za-z][A-Za-z0-9\s&\.\-]{1,20}?)\s*[:\-]?\s*(\d+)\s*(?:shares?|units?)?\b",
        re.IGNORECASE,
    )

    # Pattern 2: quantity then name ("10 shares of MRF", "15 units Reliance")
    # Strict: number + (shares|units) + (of)? + stock name 
    qty_first_pat = re.compile(
        r"(\d+)\s+(?:shares?|units?)\s+(?:of\s+)?([A-Za-z][A-Za-z0-9\s\-]{1,20}?)(?=\s*[,\.;]|\s+and|\s*$)",
        re.IGNORECASE,
    )

    for qty, raw_name in qty_first_pat.findall(message):
        _add_item(raw_name, int(qty))

    for raw_name, qty in name_first_pat.findall(message):
        _add_item(raw_name, int(qty))

    result = list(qty_by_symbol.values())
    logger.info(f"[CHAT] Portfolio extraction: extracted {len(result)} unique items from message")
    for item in result:
        logger.info(f"[CHAT]   - {item['symbol']}: {item['qty']} shares")
    return result


# ── Data-fetching helpers ──────────────────────────────────────────────────────
def _fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """
    Fetch current market snapshot for a symbol via the existing 5paisa pipeline.
    Returns a clean dict or an error dict if data is unavailable.
    """
    try:
        scrip_code = script_master_service.get_scrip_code(symbol, "N")
        if not scrip_code:
            scrip_code = script_master_service.get_scrip_code(symbol, "B")
        if not scrip_code:
            return {"symbol": symbol, "error": f"'{symbol}' not found in ScripMaster"}

        snap = market_service.get_market_snapshot(scrip_code, "N", "C")
        data_arr = (snap.get("body") or snap).get("Data", [])
        if not data_arr:
            return {"symbol": symbol, "error": "No snapshot data returned"}

        d = data_arr[0]

        def _sf(v, default=0.0):
            try:
                return float(v) if v is not None else default
            except (ValueError, TypeError):
                return default

        price = _sf(d.get("LastTradedPrice") or d.get("LastRate"))
        prev  = _sf(d.get("PClose"))
        chg   = round(price - prev, 2)
        chg_p = round((chg / prev * 100) if prev else 0.0, 2)

        return {
            "symbol":        symbol,
            "price":         round(price, 2),
            "prevClose":     round(prev, 2),
            "change":        chg,
            "changePercent": chg_p,
            "open":          round(_sf(d.get("Open") or d.get("OpenRate")), 2),
            "high":          round(_sf(d.get("High")), 2),
            "low":           round(_sf(d.get("Low")), 2),
            "volume":        int(_sf(d.get("Volume") or d.get("TotalQty"), 0)),
        }
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
        return (
            f"{sym}:\n"
            f"  Current Price : ₹{s.get('price', 0):>10,.2f}\n"
            f"  Day Change    : {sign}{s.get('changePercent', 0):.2f}%"
            f"  (₹{s.get('change', 0):+.2f})\n"
            f"  Open / High / Low: ₹{s.get('open', 0):,.2f} / "
            f"₹{s.get('high', 0):,.2f} / ₹{s.get('low', 0):,.2f}\n"
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
        "• Compare P/E ratio, EPS, revenue growth, and market cap using your knowledge of these companies.\n\n"
        "**4. Volume & Activity**\n"
        "• Compare trading volumes and what they signal about investor interest.\n\n"
        "**5. Verdict**\n"
        "• Which looks more attractive right now and one-line reason why.\n\n"
        "Be data-specific where possible. Total response under 300 words."
    )


def _prompt_portfolio(items: List[Dict], enriched: List[Dict], history: List[Dict[str, str]] = None) -> str:
    total = sum(i.get("total_value", 0) for i in enriched if not i.get("error"))

    lines = []
    for item in enriched:
        sym = item["symbol"]
        qty = item["qty"]
        if item.get("error"):
            lines.append(f"  {sym} ×{qty}  —  data unavailable ({item['error']})")
        else:
            val  = item.get("total_value", 0)
            wt   = (val / total * 100) if total else 0
            sign = "+" if item.get("changePercent", 0) >= 0 else ""
            lines.append(
                f"  {sym:<14} {qty:>4} shares  @  ₹{item.get('price', 0):>9,.2f}"
                f"  =  ₹{val:>11,.2f}  ({wt:.1f}% of portfolio)"
                f"  |  day {sign}{item.get('changePercent', 0):.2f}%"
            )

    breakdown = "\n".join(lines)
    history_str = _format_history(history)
    return (
        "You are MarketMind AI, an expert Indian portfolio analyst.\n\n"
        f"{history_str}"
        "A user has shared their stock portfolio. Below is real-time market data "
        "for each holding. Provide a concise portfolio analysis using bullet points only.\n\n"
        "=== PORTFOLIO HOLDINGS ===\n"
        f"{breakdown}\n\n"
        f"Total Portfolio Value: ₹{total:,.2f}\n\n"
        "=== PORTFOLIO ANALYSIS ===\n"
        "Use ONLY bullet points (• ). No paragraphs. 2-3 bullets per section max.\n\n"
        "**1. Portfolio Summary**\n"
        "• Total value, number of holdings, best and worst performer today.\n\n"
        "**2. Holdings Breakdown**\n"
        "• Each stock: weight %, today's change, and one-line status.\n\n"
        "**3. Diversification**\n"
        "• Sector spread, concentration risk, any over-exposure.\n\n"
        "**4. Risk Level**\n"
        "• Low / Medium / High with one-line reason.\n\n"
        "**5. Suggestions**\n"
        "• 2-3 specific, actionable recommendations.\n\n"
        "Total response under 250 words. Use Indian market context (NSE/BSE, INR)."
    )


def _prompt_stock_query(symbol: str, stock: Dict, sentiment: Dict, history: List[Dict[str, str]] = None) -> str:
    if stock.get("error"):
        return _prompt_general(f"Tell me about {symbol} stock listed on NSE India.", history)

    sign = "+" if stock.get("changePercent", 0) >= 0 else ""
    history_str = _format_history(history)
    return (
        "You are MarketMind AI, an expert Indian stock market analyst.\n\n"
        f"{history_str}"
        f"Below is real-time data and FinBERT news sentiment for {symbol} (NSE).\n\n"
        "=== LIVE MARKET DATA ===\n"
        f"Symbol        : {symbol}\n"
        f"Current Price : ₹{stock.get('price', 0):,.2f}\n"
        f"Day Change    : {sign}{stock.get('changePercent', 0):.2f}%"
        f"  (₹{stock.get('change', 0):+.2f})\n"
        f"Open          : ₹{stock.get('open', 0):,.2f}\n"
        f"High / Low    : ₹{stock.get('high', 0):,.2f} / ₹{stock.get('low', 0):,.2f}\n"
        f"Volume        : {stock.get('volume', 0):,}\n\n"
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
        "**2. News Sentiment**\n"
        "• FinBERT score, positive/negative split, investor confidence summary.\n\n"
        "**3. Technical Snapshot**\n"
        "• High/low range, volume vs typical, any notable intraday pattern.\n\n"
        "**4. Short-term Outlook**\n"
        "• Balanced 1-2 bullet view: bullish factors vs risks.\n\n"
        "**5. Key Risks**\n"
        "• 2 main risks investors should watch.\n\n"
        "Be data-specific. Reference actual numbers. Total response under 200 words."
    )


def _prompt_suggestion(message: str, history: List[Dict[str, str]] = None) -> str:
    history_str = _format_history(history)
    return (
        "You are MarketMind AI, an expert Indian investment advisor.\n\n"
        f"{history_str}"
        "A user is asking for investment recommendations. Before answering, apply these "
        "inference rules to understand their situation:\n\n"
        "INFERENCE RULES (apply even if not explicitly stated):\n"
        "• If the user mentions a salary/income/earnings figure → assume it is MONTHLY income.\n"
        "• If the user says 'invest X' alongside a monthly income → assume X is a MONTHLY investment (SIP), not a one-time lump sum.\n"
        "• 'passive' investing = index funds / ETFs, low churn. 'aggressive' = higher equity %, growth stocks.\n"
        "• 'passive aggressive' or 'moderately aggressive' = 70-80% equity, rest debt/gold.\n"
        "• If no age is mentioned, do not assume one — skip age-based advice.\n"
        "• If no risk tolerance is stated, infer it from context (e.g. 'safe' = conservative, 'grow fast' = aggressive).\n\n"
        f"User's query: {message}\n\n"
        "=== INVESTMENT RECOMMENDATION ===\n"
        "Use ONLY bullet points (• ). No paragraphs. 2-3 bullets per section max.\n\n"
        "**1. Investor Profile**\n"
        "• Monthly income, monthly investment amount, inferred risk profile — state your inferences clearly.\n\n"
        "**2. Recommended Allocation**\n"
        "• % split: large-cap equity, mid-cap, debt/bonds, gold — tailored to their risk profile.\n\n"
        "**3. Specific Picks**\n"
        "• 3-4 specific NSE stocks or index funds with one-line reason each.\n\n"
        "**4. Investment Strategy**\n"
        "• SIP amount per month, time horizon, when to review.\n\n"
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

    # ── General finance Q&A ──────────────────────────────────────────────────
    if intent == "general":
        return {
            "response": _call_ollama(_prompt_general(message, history)),
            "intent":   "general",
            "data":     None,
        }

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
        symbols = _extract_symbols(message)
        if not symbols:
            return {
                "response": _call_ollama(_prompt_general(message, history)),
                "intent":   "general",
                "data":     None,
            }

        symbol    = symbols[0]
        stock     = _fetch_stock_info(symbol)
        sentiment = _fetch_sentiment(symbol)
        prompt    = _prompt_stock_query(symbol, stock, sentiment, history)
        response  = _call_ollama(prompt)

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

    # ── Fallback ─────────────────────────────────────────────────────────────
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

    # ── General finance Q&A ──────────────────────────────────────────────────
    if intent == "general":
        yield {"type": "meta", "intent": "general", "data": None}
        for token in _stream_ollama(_prompt_general(message, history)):
            yield {"type": "token", "text": token}
        yield {"type": "done"}
        return

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
        symbols = _extract_symbols(message)
        if not symbols:
            yield {"type": "meta", "intent": "general", "data": None}
            for token in _stream_ollama(_prompt_general(message, history)):
                yield {"type": "token", "text": token}
            yield {"type": "done"}
            return

        symbol    = symbols[0]
        stock     = _fetch_stock_info(symbol)
        sentiment = _fetch_sentiment(symbol)

        yield {"type": "meta", "intent": "stock_query", "data": {"stock": stock, "sentiment": sentiment}}
        for token in _stream_ollama(_prompt_stock_query(symbol, stock, sentiment, history)):
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

    # ── Fallback ─────────────────────────────────────────────────────────────
    yield {"type": "meta", "intent": "general", "data": None}
    for token in _stream_ollama(_prompt_general(message, history)):
        yield {"type": "token", "text": token}
    yield {"type": "done"}

