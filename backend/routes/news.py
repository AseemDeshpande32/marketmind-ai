"""
News Routes Blueprint
Handles news-related API endpoints
"""

from flask import Blueprint, jsonify, request, current_app
from services.news_service import get_news_service, NewsServiceError
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
news_bp = Blueprint("news", __name__, url_prefix="/api/news")


@news_bp.route("", methods=["GET"])
def get_latest_news():
    """
    GET /api/news
    Fetch latest stock market news from external API.
    
    Query Parameters:
        - category (optional): News category filter (e.g., 'stocks', 'markets')
        - limit (optional): Number of articles to return (default: 20, max: 100)
    
    Returns:
        JSON response with news articles
        
    Example Response:
        {
            "success": true,
            "data": [
                {
                    "title": "Stock Market Hits All-Time High",
                    "description": "Markets surge as investors...",
                    "source": "Economic Times",
                    "url": "https://...",
                    "published_at": "2026-01-22T10:30:00",
                    "image_url": "https://..."
                }
            ],
            "count": 15
        }
    """
    try:
        # Get query parameters
        category = request.args.get("category", type=str)
        limit = request.args.get("limit", default=20, type=int)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({
                "success": False,
                "error": "Limit must be between 1 and 100"
            }), 400
        
        # Get news service instance
        news_service = get_news_service(
            api_key=current_app.config.get("NEWS_API_KEY"),
            api_url=current_app.config.get("NEWS_API_URL")
        )
        
        # Fetch news from external API
        result = news_service.fetch_latest_news(
            category=category,
            limit=limit
        )
        
        # Return response based on service result
        if result["success"]:
            status_code = 200
        else:
            # Service returned an error but handled gracefully
            status_code = 503 if "unavailable" in result.get("error", "").lower() else 500
        
        return jsonify(result), status_code
    
    except ValueError as e:
        # Configuration error
        logger.error(f"Configuration error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "News service is not configured properly",
            "message": "Please contact system administrator"
        }), 500
    
    except NewsServiceError as e:
        # Custom service error
        logger.error(f"News service error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch news",
            "message": str(e)
        }), 500
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in news route: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "message": "Please try again later"
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
        # Check if API key and URL are configured
        api_key = current_app.config.get("NEWS_API_KEY")
        api_url = current_app.config.get("NEWS_API_URL")
        
        if not api_key or api_key == "your-news-api-key-here":
            return jsonify({
                "status": "unhealthy",
                "message": "News API key not configured",
                "configured": False
            }), 503
        
        if not api_url:
            return jsonify({
                "status": "unhealthy",
                "message": "News API URL not configured",
                "configured": False
            }), 503
        
        return jsonify({
            "status": "healthy",
            "message": "News service is configured",
            "configured": True
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
