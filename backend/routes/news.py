"""
News Routes Blueprint
Handles news-related API endpoints
"""

from flask import Blueprint, jsonify, request, current_app
from services.newsapi_service import NewsAPIService
from services.newsdata_service import NewsDataService
from services.news_service import get_news_service
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
news_bp = Blueprint("news", __name__, url_prefix="/api/news")


@news_bp.route("", methods=["GET"])
def get_latest_news():
    """
    GET /api/news
    Fetch latest stock market news.
    Primary source: Alpha Vantage NEWS_SENTIMENT (includes sentiment labels).
    Fallback sources: NewsData.io then NewsAPI.org (labels may be defaulted).
    
    Query Parameters:
        - limit (optional): Number of articles to return (default: 20, max: 100)
    
    Returns:
        JSON response with news articles
    """
    try:
        # Get query parameters
        limit = request.args.get("limit", default=20, type=int)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({
                "success": False,
                "error": "Limit must be between 1 and 100"
            }), 400
        
        # Prefer Alpha Vantage because it returns article-level sentiment labels.
        news_api_key = current_app.config.get("NEWS_API_KEY")
        news_api_url = current_app.config.get("NEWS_API_URL")
        result = None

        if news_api_key and news_api_url:
            try:
                alpha_service = get_news_service(news_api_key, news_api_url)
                result = alpha_service.fetch_latest_news(category=request.args.get("category"), limit=limit)
                if result.get("success"):
                    result["provider"] = "alphavantage"
                    # If primary provider returns an empty successful payload,
                    # allow fallback provider to try filling the feed.
                    alpha_count = result.get("count")
                    if alpha_count is None:
                        alpha_count = len(result.get("data") or [])
                    if alpha_count == 0:
                        logger.info("Alpha Vantage returned 0 articles; trying fallback providers")
                        result = None
            except Exception as alpha_exc:
                logger.warning(f"Alpha Vantage news failed, falling back to other providers: {alpha_exc}")

        # Fallback 1: NewsData.io (India-focused)
        if not result or not result.get("success"):
            newsdata_key = current_app.config.get("NEWSDATA_API_KEY")
            if newsdata_key:
                try:
                    newsdata_country = current_app.config.get("NEWSDATA_COUNTRY", "in")
                    newsdata_service = NewsDataService(newsdata_key, newsdata_country)
                    result = newsdata_service.fetch_latest_news(
                        limit=limit,
                        category=request.args.get("category")
                    )
                    if result.get("success"):
                        result["provider"] = "newsdata"
                except Exception as newsdata_exc:
                    logger.warning(f"NewsData fallback failed, trying NewsAPI: {newsdata_exc}")

        # Fallback 2: NewsAPI.org
        if not result or not result.get("success"):
            newsapi_key = current_app.config.get("NEWSAPI_KEY")
            if not newsapi_key:
                return jsonify({
                    "success": False,
                    "error": "No configured news provider is available"
                }), 500

            news_service = NewsAPIService(newsapi_key)
            result = news_service.fetch_latest_news(limit=limit)
            if result.get("success"):
                result["provider"] = "newsapi"
        
        # Return response
        if result["success"]:
            status_code = 200
        else:
            status_code = 503
        
        return jsonify(result), status_code
    
    except ValueError as e:
        # Configuration error
        logger.error(f"Configuration error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "News service is not configured properly",
            "message": str(e)
        }), 500
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in news route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "message": str(e)
        }), 500


@news_bp.route("/health", methods=["GET"])
def news_health_check():
    """
    GET /api/news/health
    Check if news service is properly configured and reachable.
    
    Returns:
        JSON response with health status
    """
    try:
        # Consider healthy if at least one provider is configured.
        alpha_key = current_app.config.get("NEWS_API_KEY")
        alpha_url = current_app.config.get("NEWS_API_URL")
        newsdata_key = current_app.config.get("NEWSDATA_API_KEY")
        newsapi_key = current_app.config.get("NEWSAPI_KEY")

        provider_config = {
            "alphavantage": bool(alpha_key and alpha_url),
            "newsdata": bool(newsdata_key),
            "newsapi": bool(newsapi_key),
        }

        if not any(provider_config.values()):
            return jsonify({
                "status": "unhealthy",
                "message": "No news provider configured",
                "configured": False,
                "providers": provider_config,
            }), 503
        
        return jsonify({
            "status": "healthy",
            "message": "News service is configured",
            "configured": True,
            "providers": provider_config,
        }), 200
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "message": "Health check failed",
            "configured": False
        }), 500


@news_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for news routes."""
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "message": "The requested news endpoint does not exist"
    }), 404


@news_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors for news routes."""
    return jsonify({
        "success": False,
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405
