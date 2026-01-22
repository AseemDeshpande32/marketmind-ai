"""
News Service Module
Handles fetching market news from Alpha Vantage NEWS_SENTIMENT API
"""

import requests # type: ignore
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsServiceError(Exception):
    """Custom exception for news service errors."""
    pass


class NewsService:
    """Service class for fetching stock market news from Alpha Vantage API."""
    
    def __init__(self, api_key: str, api_url: str):
        """
        Initialize NewsService with API credentials.
        
        Args:
            api_key: API key for authentication
            api_url: Base URL for the news API
        """
        if not api_key or api_key == "your-news-api-key-here":
            raise ValueError("NEWS_API_KEY is not configured properly")
        
        if not api_url:
            raise ValueError("NEWS_API_URL is not configured properly")
        
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = 10  # Request timeout in seconds
        # Alpha Vantage uses query parameters for API key, not headers
        self.headers = {
            "User-Agent": "MarketMind-AI/1.0"
        }
    
    def fetch_latest_news(
        self, 
        category: Optional[str] = None, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch latest market news from Alpha Vantage API.
        
        Args:
            category: Optional news category filter (e.g., 'stocks', 'markets')
            limit: Maximum number of articles to return (default: 20)
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating if request was successful
                - data: List of news articles
                - count: Number of articles returned
                - error: Error message if any
        
        Raises:
            NewsServiceError: If API request fails critically
        """
        try:
            # Prepare query parameters for Alpha Vantage
            params = {
                "function": "NEWS_SENTIMENT",
                "apikey": self.api_key,
                "limit": min(limit, 1000),  # Alpha Vantage supports up to 1000
            }
            
            # Alpha Vantage uses 'topics' parameter for filtering
            if category:
                # Map common categories to Alpha Vantage topics
                topic_map = {
                    "stocks": "financial_markets",
                    "markets": "financial_markets",
                    "economy": "economy_macro",
                    "technology": "technology",
                    "earnings": "earnings"
                }
                params["topics"] = topic_map.get(category.lower(), category)
            
            logger.info(f"Fetching news from Alpha Vantage API: {self.api_url}")
            
            # Make API request
            response = requests.get(
                self.api_url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            # Handle HTTP errors
            if response.status_code == 401:
                logger.error("API authentication failed - invalid API key")
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": "Authentication failed with news provider"
                }
            
            if response.status_code == 429:
                logger.warning("API rate limit exceeded")
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": "Rate limit exceeded, please try again later"
                }
            
            if response.status_code == 503:
                logger.error("News API service unavailable")
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": "News service temporarily unavailable"
                }
            
            # Raise exception for other HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            # Extract and clean news articles
            articles = self._extract_articles(data)
            
            if not articles:
                logger.warning("No news articles found in API response")
                return {
                    "success": True,
                    "data": [],
                    "count": 0,
                    "message": "No news articles available at the moment"
                }
            
            logger.info(f"Successfully fetched {len(articles)} news articles")
            
            return {
                "success": True,
                "data": articles,
                "count": len(articles)
            }
        
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.timeout} seconds")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "Request timeout - news service took too long to respond"
            }
        
        except requests.exceptions.ConnectionError:
            logger.error("Connection error - unable to reach news API")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "Unable to connect to news service"
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "Failed to fetch news from external service"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": "An unexpected error occurred while fetching news"
            }
    
    def _extract_articles(self, raw_data: Dict) -> List[Dict[str, Any]]:
        """
        Extract and clean article data from raw API response.
        Alpha Vantage specific format.
        
        Args:
            raw_data: Raw JSON response from API
        
        Returns:
            List of cleaned article dictionaries
        """
        articles = []
        
        # Alpha Vantage returns 'feed' array
        raw_articles = raw_data.get("feed", [])
        
        for article in raw_articles:
            try:
                cleaned_article = {
                    "title": self._clean_string(article.get("title")),
                    "description": self._clean_string(article.get("summary")),
                    "source": self._clean_string(article.get("source")),
                    "url": article.get("url"),
                    "published_at": self._format_date(article.get("time_published")),
                    "image_url": article.get("banner_image"),
                    "sentiment": {
                        "label": article.get("overall_sentiment_label"),
                        "score": article.get("overall_sentiment_score")
                    } if article.get("overall_sentiment_label") else None
                }
                
                # Only include articles with at least title and URL
                if cleaned_article["title"] and cleaned_article["url"]:
                    articles.append(cleaned_article)
                
            except Exception as e:
                logger.warning(f"Error processing article: {str(e)}")
                continue
        
        return articles
    
    def _clean_string(self, value: Any) -> Optional[str]:
        """
        Clean and sanitize string values.
        
        Args:
            value: Input value to clean
        
        Returns:
            Cleaned string or None
        """
        if not value:
            return None
        
        try:
            return str(value).strip()
        except:
            return None
    
    def _format_date(self, date_value: Any) -> Optional[str]:
        """
        Format date to ISO 8601 string.
        Alpha Vantage uses format: YYYYMMDDTHHMMSS
        
        Args:
            date_value: Date value (string, datetime, or timestamp)
        
        Returns:
            ISO formatted date string or None
        """
        if not date_value:
            return None
        
        try:
            # If already a string
            if isinstance(date_value, str):
                # Alpha Vantage format: "20260122T103000"
                if len(date_value) == 15 and 'T' in date_value:
                    dt = datetime.strptime(date_value, "%Y%m%dT%H%M%S")
                    return dt.isoformat()
                # Try standard ISO format
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return dt.isoformat()
            
            # If datetime object
            if isinstance(date_value, datetime):
                return date_value.isoformat()
            
            # If timestamp (int/float)
            if isinstance(date_value, (int, float)):
                dt = datetime.fromtimestamp(date_value)
                return dt.isoformat()
            
            return None
        
        except Exception as e:
            logger.warning(f"Error formatting date: {str(e)}")
            return str(date_value) if date_value else None


# Singleton instance (initialized in routes)
_news_service_instance: Optional[NewsService] = None


def get_news_service(api_key: str = None, api_url: str = None) -> NewsService:
    """
    Get or create singleton instance of NewsService.
    
    Args:
        api_key: API key for the news service
        api_url: Base URL for the news API
    
    Returns:
        NewsService instance
    """
    global _news_service_instance
    
    if _news_service_instance is None:
        if not api_key or not api_url:
            raise ValueError("API key and URL required for first initialization")
        _news_service_instance = NewsService(api_key, api_url)
    
    return _news_service_instance
