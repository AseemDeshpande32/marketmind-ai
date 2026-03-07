"""
FinBERT News Sentiment Analysis Service
Analyzes financial news sentiment using ProsusAI/finbert model.
"""

import re
import logging
import feedparser
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# ── FinBERT model (lazy-loaded on first use) ──────────────────────────────────
_tokenizer = None
_model = None
MODEL_NAME = "ProsusAI/finbert"

FINANCIAL_KEYWORDS = [
    "stock", "shares", "earnings", "revenue", "profit", "market",
    "analyst", "price target", "bullish", "bearish", "invest",
    "dividend", "quarter", "fiscal", "ipo", "listing", "nse", "bse",
    "sensex", "nifty", "equity", "fund", "portfolio",
]


def _load_model():
    """Lazy-load the FinBERT tokenizer and model."""
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        logger.info("Loading FinBERT model (ProsusAI/finbert) — first run may take a moment…")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        _model.eval()
        logger.info("FinBERT model loaded successfully.")
    return _tokenizer, _model


# ── Pipeline steps ─────────────────────────────────────────────────────────────

def fetch_news(stock_name: str, max_articles: int = 15) -> list[dict]:
    """
    Step 1 — Fetch latest news from Google News RSS.

    Args:
        stock_name: Company / stock name to search for.
        max_articles: Maximum number of articles to fetch.

    Returns:
        List of dicts with keys: title, description, link.
    """
    query = stock_name.replace(" ", "+") + "+stock"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries[:max_articles]:
        title = entry.get("title", "")
        # Clean HTML tags from description/summary
        raw_desc = entry.get("summary", entry.get("description", ""))
        description = re.sub(r"<[^>]+>", " ", raw_desc).strip()
        link = entry.get("link", "")
        articles.append({"title": title, "description": description, "link": link})

    logger.info("Fetched %d articles for '%s'", len(articles), stock_name)
    return articles


def filter_relevant_news(articles: list[dict]) -> list[dict]:
    """
    Step 3 — Keep only articles that contain financial / stock-related keywords.

    Args:
        articles: Raw list of articles from fetch_news().

    Returns:
        Filtered list of relevant articles.
    """
    relevant = []
    for article in articles:
        combined = (article["title"] + " " + article["description"]).lower()
        if any(kw in combined for kw in FINANCIAL_KEYWORDS):
            relevant.append(article)

    logger.info("Kept %d relevant articles after filtering.", len(relevant))
    return relevant


def remove_duplicates(articles: list[dict]) -> list[dict]:
    """
    Step 4 — Remove duplicate headlines (same title from multiple sources).

    Args:
        articles: Filtered list of articles.

    Returns:
        De-duplicated list of articles.
    """
    seen_titles: set[str] = set()
    unique = []
    for article in articles:
        # Normalise title: lowercase, strip punctuation, truncate to first 60 chars
        norm = re.sub(r"[^a-z0-9 ]", "", article["title"].lower())[:60].strip()
        if norm and norm not in seen_titles:
            seen_titles.add(norm)
            unique.append(article)

    logger.info("Removed duplicates: %d → %d articles.", len(articles), len(unique))
    return unique


def analyze_sentiment(articles: list[dict]) -> list[dict]:
    """
    Step 5 — Run FinBERT inference on each article.

    Args:
        articles: De-duplicated, filtered article list.

    Returns:
        List of dicts adding keys: positive, neutral, negative (probabilities).
    """
    tokenizer, model = _load_model()
    results = []

    for article in articles:
        # Step 2: combine title + description into one text string
        text = (article["title"] + ". " + article["description"]).strip()
        # Truncate to avoid exceeding max token length
        text = text[:512]

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1).squeeze().tolist()

        # FinBERT label order: positive=0, negative=1, neutral=2
        label_map = model.config.id2label
        prob_dict = {label_map[i].lower(): round(probs[i], 4) for i in range(len(probs))}

        results.append({**article, **prob_dict})

    return results


def compute_sentiment_score(analyzed: list[dict]) -> dict:
    """
    Steps 6 & 7 — Compute per-article scores, average them, and derive
    overall sentiment.

    Args:
        analyzed: Articles annotated with positive / neutral / negative probabilities.

    Returns:
        Dict with positive_percent, neutral_percent, negative_percent,
        sentiment_score, overall_sentiment.
    """
    if not analyzed:
        return {
            "positive_percent": 0,
            "neutral_percent": 0,
            "negative_percent": 0,
            "sentiment_score": 0.0,
            "overall_sentiment": "Neutral",
            "articles_analyzed": 0,
        }

    total_pos = total_neu = total_neg = 0.0
    scores = []

    for article in analyzed:
        pos = article.get("positive", 0.0)
        neu = article.get("neutral", 0.0)
        neg = article.get("negative", 0.0)
        total_pos += pos
        total_neu += neu
        total_neg += neg
        scores.append(pos - neg)  # per-article sentiment score

    n = len(analyzed)
    avg_score = sum(scores) / n

    pos_pct = round((total_pos / n) * 100, 1)
    neu_pct = round((total_neu / n) * 100, 1)
    neg_pct = round((total_neg / n) * 100, 1)

    # Step 7: nuanced sentiment labels
    # If the leading category has a clear majority (>= 50%) use strong labels,
    # otherwise fall back to nuanced / hedged labels.
    top_pct = max(pos_pct, neu_pct, neg_pct)
    has_clear_majority = top_pct >= 50

    if has_clear_majority:
        if avg_score > 0.2:
            overall = "Bullish"
        elif avg_score < -0.2:
            overall = "Bearish"
        else:
            overall = "Neutral"
    else:
        # No single category dominates — use nuanced labels
        if avg_score > 0.1:
            overall = "Slightly Bullish"
        elif avg_score < -0.1:
            overall = "Slightly Bearish"
        else:
            overall = "Mixed"

    return {
        "positive_percent":  pos_pct,
        "neutral_percent":   neu_pct,
        "negative_percent":  neg_pct,
        "sentiment_score":   round(avg_score, 4),
        "overall_sentiment": overall,
        "articles_analyzed": n,
    }


# ── Public entry point ────────────────────────────────────────────────────────

def run_sentiment_pipeline(stock_name: str, ticker: str) -> dict:
    """
    Full pipeline: fetch → filter → deduplicate → analyse → score.

    Args:
        stock_name: Human-readable company name (e.g. "Reliance Industries").
        ticker: Stock ticker (e.g. "RELIANCE.NS") — used as fallback query.

    Returns:
        Sentiment summary dict ready to be returned as JSON.
    """
    # Use the cleaner of the two names as primary query
    query_name = stock_name if stock_name else ticker.split(".")[0]

    articles    = fetch_news(query_name)

    # Fallback: if too few articles, retry with ticker base
    if len(articles) < 3 and ticker:
        ticker_base = ticker.split(".")[0]
        if ticker_base.lower() != query_name.lower():
            articles = fetch_news(ticker_base)

    relevant    = filter_relevant_news(articles)
    unique      = remove_duplicates(relevant)

    # Need at least 1 article to run FinBERT
    if not unique:
        return {
            "positive_percent": 0,
            "neutral_percent": 100,
            "negative_percent": 0,
            "sentiment_score": 0.0,
            "overall_sentiment": "Neutral",
            "articles_analyzed": 0,
            "message": "No relevant financial news found.",
        }

    analyzed = analyze_sentiment(unique)
    result   = compute_sentiment_score(analyzed)
    return result
