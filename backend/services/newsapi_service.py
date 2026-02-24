"""
NewsAPI.org News Service Module
Handles fetching market news from NewsAPI.org
"""

import requests
from typing import Dict, List, Any
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsAPIService:
    """Service class for fetching news from NewsAPI.org."""
    
    def __init__(self, api_key: str):
        """
        Initialize NewsAPIService.
        
        Args:
            api_key: API key for NewsAPI.org authentication
        """
        if not api_key:
            raise ValueError("NEWSAPI_KEY is not configured properly")
        
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.timeout = 10
    
    def fetch_latest_news(self, limit: int = 20) -> Dict[str, Any]:
        """
        Fetch latest financial news from NewsAPI.org.
        
        Args:
            limit: Maximum number of articles to return (default: 20)
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating if request was successful
                - data: List of news articles
                - count: Number of articles returned
                - error: Error message if any
        """
        try:
            # Search for financial/business news
            params = {
                'apiKey': self.api_key,
                'q': 'stock market OR business OR finance OR economy',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': min(limit, 100)
            }
            
            logger.info(f"Fetching news from NewsAPI.org")
            
            response = requests.get(
                f"{self.base_url}/everything",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 401:
                logger.error("NewsAPI authentication failed - invalid API key")
                return {
                    'success': False,
                    'data': [],
                    'count': 0,
                    'error': 'Invalid API key'
                }
            
            if response.status_code == 429:
                logger.error("NewsAPI rate limit exceeded")
                return {
                    'success': False,
                    'data': [],
                    'count': 0,
                    'error': 'Rate limit exceeded'
                }
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data.get('message')}")
                return {
                    'success': False,
                    'data': [],
                    'count': 0,
                    'error': data.get('message', 'Failed to fetch news')
                }
            
            articles = data.get('articles', [])
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI")
            
            # Transform to our format
            transformed_news = []
            for article in articles[:limit]:
                # Skip articles with [Removed] content
                if article.get('title') == '[Removed]':
                    continue
                    
                transformed_news.append({
                    'title': article.get('title', 'No title'),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published_at': article.get('publishedAt', datetime.now().isoformat()),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'image_url': article.get('urlToImage'),
                    'sentiment': {
                        'label': 'Neutral',
                        'score': 0
                    }
                })
            
            return {
                'success': True,
                'data': transformed_news,
                'count': len(transformed_news),
                'error': None
            }
            
        except requests.exceptions.Timeout:
            logger.error("NewsAPI request timed out")
            return {
                'success': False,
                'data': [],
                'count': 0,
                'error': 'Request timed out'
            }
        except Exception as e:
            logger.error(f"Error fetching news from NewsAPI: {e}")
            return {
                'success': False,
                'data': [],
                'count': 0,
                'error': str(e)
            }
