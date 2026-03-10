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
import logging
import requests
from typing import Any, Dict, List

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


# ── Intent detection ───────────────────────────────────────────────────────────
def _detect_intent(message: str) -> str:
    """
    Classify user message into one of:
      'comparison' | 'portfolio' | 'stock_query' | 'general'
    """
    if any(p.search(message) for p in _COMPARE_RE):
        return "comparison"
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


def _extract_portfolio_items(message: str) -> List[Dict[str, Any]]:
    """
    Parse portfolio items from messages such as:
      "TCS 5, Infosys 10, Reliance 3"
      "TCS:5 INFY:10 RELIANCE:3"
      "I have TCS - 5 shares and Infosys - 10 shares"
    Returns list of dicts: { symbol, name, qty }
    """
    items: List[Dict[str, Any]] = []
    seen: set = set()

    # Pattern: word(s) followed by optional separator and a number
    pat = re.compile(
        r"([A-Za-z][A-Za-z0-9\s&\.\-]{0,30}?)\s*[:\-]?\s*(\d+)\s*(?:shares?|units?)?",
        re.IGNORECASE,
    )

    for match in pat.finditer(message):
        raw_name = match.group(1).strip().rstrip("- ").strip()
        qty = int(match.group(2))
        if qty == 0 or not raw_name:
            continue

        name_lower = raw_name.lower()
        # Resolve symbol
        symbol = raw_name.upper()
        for key in sorted(KNOWN_STOCKS, key=len, reverse=True):
            if key in name_lower:
                symbol = KNOWN_STOCKS[key]
                break

        if symbol not in seen:
            seen.add(symbol)
            items.append({"symbol": symbol, "name": raw_name.strip(), "qty": qty})

    return items


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


# ── Prompt templates ───────────────────────────────────────────────────────────
def _prompt_general(message: str) -> str:
    return (
        "You are MarketMind AI, an intelligent Indian stock market assistant "
        "specialising in NSE/BSE listed companies, financial concepts, and "
        "investment analysis.\n\n"
        "Answer the following question clearly and concisely. When explaining "
        "financial concepts, use examples relevant to Indian markets (NSE/BSE, INR).\n\n"
        f"User Question: {message}\n\n"
        "Provide a helpful, accurate, and well-structured answer:"
    )


def _prompt_comparison(
    sym_a: str, sym_b: str,
    stock_a: Dict, stock_b: Dict,
    sent_a: Dict, sent_b: Dict,
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
            f"(score {sent.get('sentiment_score', 0):.2f} | "
            f"+{sent.get('positive_percent', 0):.0f}% pos / "
            f"{sent.get('neutral_percent', 0):.0f}% neu / "
            f"{sent.get('negative_percent', 0):.0f}% neg | "
            f"{sent.get('articles_analyzed', 0)} articles)"
        )

    return (
        "You are MarketMind AI, an expert Indian stock market analyst.\n\n"
        "Below is real-time market data and FinBERT news sentiment for two "
        "NSE-listed stocks. Write a thorough, data-driven comparison report.\n\n"
        "=== LIVE MARKET DATA ===\n"
        f"{_block(sym_a, stock_a, sent_a)}\n\n"
        f"{_block(sym_b, stock_b, sent_b)}\n\n"
        "=== COMPARISON REPORT STRUCTURE ===\n"
        "Write your response with exactly these five sections:\n\n"
        "**1. Price Comparison**\n"
        "Compare current prices, daily movement, and intraday trading range.\n\n"
        "**2. Sentiment Comparison**\n"
        "Analyse and contrast the FinBERT news sentiment scores for both stocks.\n\n"
        "**3. Business & Growth Analysis**\n"
        "Discuss each company's sector position and growth prospects in the Indian market.\n\n"
        "**4. Key Insights**\n"
        "Highlight the most important similarities and differences based on the data.\n\n"
        "**5. Conclusion**\n"
        "State which stock looks more attractive for investors right now and why.\n\n"
        "Be specific and reference the numbers provided above."
    )


def _prompt_portfolio(items: List[Dict], enriched: List[Dict]) -> str:
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
    return (
        "You are MarketMind AI, an expert Indian portfolio analyst.\n\n"
        "A user has shared their stock portfolio. Below is real-time market data "
        "for each holding. Provide a comprehensive portfolio analysis.\n\n"
        "=== PORTFOLIO HOLDINGS ===\n"
        f"{breakdown}\n\n"
        f"Total Portfolio Value: ₹{total:,.2f}\n\n"
        "=== PORTFOLIO ANALYSIS STRUCTURE ===\n"
        "Write your response with exactly these five sections:\n\n"
        "**1. Total Portfolio Value**\n"
        "State the total value and provide a brief summary of holdings.\n\n"
        "**2. Stock-wise Breakdown**\n"
        "Analyse each stock's weight, current performance, and contribution.\n\n"
        "**3. Diversification Analysis**\n"
        "Evaluate sector distribution, concentration risk, and overall balance.\n\n"
        "**4. Risk Assessment**\n"
        "Give an overall risk level (Low / Medium / High) with clear reasoning.\n\n"
        "**5. Actionable Suggestions**\n"
        "Provide 3-5 specific, practical recommendations to improve this portfolio.\n\n"
        "Reference actual data. Tailor response to the Indian market context (NSE/BSE, INR)."
    )


def _prompt_stock_query(symbol: str, stock: Dict, sentiment: Dict) -> str:
    if stock.get("error"):
        return _prompt_general(f"Tell me about {symbol} stock listed on NSE India.")

    sign = "+" if stock.get("changePercent", 0) >= 0 else ""
    return (
        "You are MarketMind AI, an expert Indian stock market analyst.\n\n"
        f"Below is real-time data and FinBERT news sentiment for {symbol} (NSE).\n\n"
        "=== LIVE MARKET DATA ===\n"
        f"Symbol        : {symbol}\n"
        f"Current Price : ₹{stock.get('price', 0):,.2f}\n"
        f"Day Change    : {sign}{stock.get('changePercent', 0):.2f}%"
        f"  (₹{stock.get('change', 0):+.2f})\n"
        f"Open          : ₹{stock.get('open', 0):,.2f}\n"
        f"High / Low    : ₹{stock.get('high', 0):,.2f} / ₹{stock.get('low', 0):,.2f}\n"
        f"Volume        : {stock.get('volume', 0):,}\n\n"
        "=== NEWS SENTIMENT (FinBERT) ===\n"
        f"Overall       : {sentiment.get('overall_sentiment', 'N/A')}"
        f"  (score {sentiment.get('sentiment_score', 0):.2f})\n"
        f"Breakdown     : +{sentiment.get('positive_percent', 0):.0f}% Positive"
        f"  |  {sentiment.get('neutral_percent', 0):.0f}% Neutral"
        f"  |  {sentiment.get('negative_percent', 0):.0f}% Negative\n"
        f"Articles      : {sentiment.get('articles_analyzed', 0)} analysed\n\n"
        "=== STOCK ANALYSIS STRUCTURE ===\n"
        "Write your response with exactly these five sections:\n\n"
        "**1. Current Market Status**\n"
        "Describe the price action and what today's movement signals.\n\n"
        "**2. Sentiment Analysis**\n"
        "Explain what the FinBERT news sentiment reveals about investor confidence.\n\n"
        "**3. Technical Snapshot**\n"
        "Read the high/low/volume data for notable intraday patterns.\n\n"
        "**4. Short-term Outlook**\n"
        "Based on the data, give a balanced short-term view.\n\n"
        "**5. Key Risk Factors**\n"
        "List the main risks investors should watch out for.\n\n"
        "Be specific and data-driven."
    )


# ── Main agent entry point ─────────────────────────────────────────────────────
def process_chat(message: str) -> Dict[str, Any]:
    """
    Main agent function called by the /api/chat route.

    1. Detects user intent.
    2. Fetches live data (stock price, sentiment) when required.
    3. Builds a structured prompt.
    4. Calls Ollama (Gemma) and returns the response.

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
            "response": _call_ollama(_prompt_general(message)),
            "intent":   "general",
            "data":     None,
        }

    # ── Stock comparison ─────────────────────────────────────────────────────
    if intent == "comparison":
        symbols = _extract_symbols(message)
        if len(symbols) < 2:
            # Not enough symbols — fall back to a general LLM answer
            return {
                "response": _call_ollama(_prompt_general(message)),
                "intent":   "comparison_fallback",
                "data":     None,
            }

        sym_a, sym_b = symbols[0], symbols[1]
        logger.info("[CHAT] Comparing %s vs %s", sym_a, sym_b)

        stock_a = _fetch_stock_info(sym_a)
        stock_b = _fetch_stock_info(sym_b)
        sent_a  = _fetch_sentiment(sym_a)
        sent_b  = _fetch_sentiment(sym_b)

        prompt   = _prompt_comparison(sym_a, sym_b, stock_a, stock_b, sent_a, sent_b)
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
                "response": _call_ollama(_prompt_general(message)),
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

        prompt   = _prompt_portfolio(items, enriched)
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
                "response": _call_ollama(_prompt_general(message)),
                "intent":   "general",
                "data":     None,
            }

        symbol    = symbols[0]
        stock     = _fetch_stock_info(symbol)
        sentiment = _fetch_sentiment(symbol)
        prompt    = _prompt_stock_query(symbol, stock, sentiment)
        response  = _call_ollama(prompt)

        return {
            "response": response,
            "intent":   "stock_query",
            "data":     {"stock": stock, "sentiment": sentiment},
        }

    # ── Fallback ─────────────────────────────────────────────────────────────
    return {
        "response": _call_ollama(_prompt_general(message)),
        "intent":   "general",
        "data":     None,
    }
