"""
MarketMind AI - Flask Application Factory
Phase 1 Backend
"""

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_class=Config):
    """
    Application factory pattern for Flask app creation.
    
    Args:
        config_class: Configuration class to use (default: Config)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CORS for cross-origin requests
    CORS(app)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.stocks import stocks_bp
    from routes.news import news_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(stocks_bp)
    app.register_blueprint(news_bp)

    # Health check endpoint
    @app.route("/")
    def health_check():
        """API health check endpoint."""
        return jsonify({"status": "MarketMind backend running"}), 200

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired JWT tokens."""
        return jsonify({
            "error": "Token has expired",
            "message": "Please log in again"
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid JWT tokens."""
        return jsonify({
            "error": "Invalid token",
            "message": "Token verification failed"
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handle missing JWT tokens."""
        return jsonify({
            "error": "Authorization required",
            "message": "Access token is missing"
        }), 401

    return app