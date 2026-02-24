"""
Configuration settings for MarketMind AI Backend
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class."""
    
    # Flask secret key for session management
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Token expires in 24 hours
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Enable connection health checks
    }
    
    # News API Configuration
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    NEWS_API_URL = os.getenv("NEWS_API_URL")
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # NewsAPI.org key
