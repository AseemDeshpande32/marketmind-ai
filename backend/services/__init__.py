"""
Services Package Initializer
"""

from .news_service import NewsService, get_news_service, NewsServiceError

__all__ = ["NewsService", "get_news_service", "NewsServiceError"]
