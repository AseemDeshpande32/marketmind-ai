"""
NewsData.io News Service Module
Handles fetching India-focused business/market news from NewsData.io
"""

from datetime import datetime
from typing import Any, Dict, List
import logging
import requests

logger = logging.getLogger(__name__)


class NewsDataService:
    """Service class for fetching market news from NewsData.io."""

    def __init__(self, api_key: str, country: str = "in"):
        if not api_key:
            raise ValueError("NEWSDATA_API_KEY is not configured properly")

        self.api_key = api_key
        self.country = country or "in"
        self.base_url = "https://newsdata.io/api/1/latest"
        self.timeout = 10

    def fetch_latest_news(self, limit: int = 20, category: str = None) -> Dict[str, Any]:
        """Fetch latest news from NewsData.io in a normalized payload."""
        try:
            params = {
                "apikey": self.api_key,
                "country": self.country,
                "language": "en",
                "category": "business",
            }

            # Optional keyword for category context to improve relevance.
            if category:
                params["q"] = category
            else:
                params["q"] = "stock market OR finance OR economy OR business"

            response = requests.get(self.base_url, params=params, timeout=self.timeout)

            if response.status_code in (401, 403):
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": "NewsData authentication failed"
                }

            if response.status_code == 429:
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": "NewsData rate limit exceeded"
                }

            response.raise_for_status()
            payload = response.json()

            if payload.get("status") != "success":
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": payload.get("results", {}).get("message")
                    or payload.get("message")
                    or "Failed to fetch from NewsData"
                }

            raw_items = payload.get("results") or []
            transformed: List[Dict[str, Any]] = []

            for article in raw_items[:limit]:
                title = (article.get("title") or "").strip()
                link = article.get("link")
                if not title or not link:
                    continue

                transformed.append({
                    "title": title,
                    "description": article.get("description") or "",
                    "source": article.get("source_name") or "NewsData",
                    "url": link,
                    "published_at": self._normalize_date(article.get("pubDate")),
                    "image_url": article.get("image_url"),
                    "sentiment": {
                        "label": "Neutral",
                        "score": 0
                    }
                })

            return {
                "success": True,
                "data": transformed,
                "count": len(transformed)
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "NewsData request timed out"
            }
        except requests.exceptions.RequestException as exc:
            logger.error("NewsData request failed: %s", exc)
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "Failed to fetch news from NewsData"
            }
        except Exception as exc:
            logger.error("Unexpected NewsData error: %s", exc)
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "Unexpected NewsData error"
            }

    def _normalize_date(self, value: Any) -> str:
        if not value:
            return datetime.utcnow().isoformat()

        try:
            # NewsData commonly returns ISO-like values with Z suffix.
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
            return str(value)
        except Exception:
            return str(value)
