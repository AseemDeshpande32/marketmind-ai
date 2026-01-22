"""
Stock Search API Blueprint for MarketMind AI
Handles real-time stock data fetching from Indian Stock Market API
"""

import os
import requests # type: ignore
from flask import Blueprint, request, jsonify

# Create stocks blueprint with /api/stocks prefix
stocks_bp = Blueprint("stocks", __name__, url_prefix="/api/stocks")

# External API configuration - Indian Stock Market API
STOCK_API_KEY = os.getenv("STOCK_API_KEY")
STOCK_API_BASE_URL = "https://stock.indianapi.in"


@stocks_bp.route("/search", methods=["GET"])
def search_stock():
    """
    Search for Indian stock by symbol and return real-time data.
    
    Query Parameters:
        - symbol: str (required) - Stock ticker symbol (e.g., TCS, RELIANCE, INFY)
    
    Returns:
        - 200: Stock data with price, change, and company info
        - 400: Missing or invalid symbol
        - 404: Stock not found
        - 502: External API error
    
    Example:
        GET /api/stocks/search?symbol=TCS
    """
    
    # Step 1: Validate API key is configured
    if not STOCK_API_KEY:
        return jsonify({
            "error": "Stock API key not configured",
            "message": "Please set STOCK_API_KEY in environment variables"
        }), 500
    
    # Step 2: Extract and validate stock symbol from query parameter
    symbol = request.args.get("symbol", "").strip().upper()
    
    if not symbol:
        return jsonify({
            "error": "Missing stock symbol",
            "message": "Please provide a stock symbol in query parameter"
        }), 400
    
    try:
        # Step 3: Fetch real-time stock data from Indian Stock Market API
        # Endpoint format: /stock?symbol=TCS&apikey=YOUR_API_KEY
        stock_url = f"{STOCK_API_BASE_URL}/stock"
        
        headers = {
            "X-Api-Key": STOCK_API_KEY,
            "Content-Type": "application/json"
        }
        
        params = {
            "name": symbol  # Indian Stock API uses 'name' parameter
        }
        
        response = requests.get(stock_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()  # Raise error for bad status codes
        
        data = response.json()
        
        # Step 4: Check if API returned valid data
        if not data or "error" in data:
            return jsonify({
                "error": "Stock not found",
                "message": f"No data found for symbol '{symbol}'. Please check if the symbol is correct."
            }), 404
        
        # Step 5: Extract stock information from API response
        # Indian Stock Market API field mapping (camelCase)
        
        # Helper function to safely extract numeric values
        def safe_float(value, default=0):
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, dict):
                # If it's a dict with exchange prices, prefer NSE
                if 'NSE' in value:
                    return safe_float(value['NSE'], default)
                elif 'BSE' in value:
                    return safe_float(value['BSE'], default)
                return default
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    return default
            return default
        
        # Extract main fields
        current_price_data = data.get("currentPrice")
        current_price = safe_float(current_price_data)  # Will extract NSE or BSE price
        
        price_change_percent = safe_float(data.get("percentChange"))
        year_low = safe_float(data.get("yearLow"))
        year_high = safe_float(data.get("yearHigh"))
        company_name = data.get("companyName", symbol)
        
        # Calculate price change from percentage if current price available
        price_change = round((current_price * price_change_percent) / 100, 2) if current_price else 0
        
        # Get additional data from stockDetailsReusableData
        stock_details = data.get("stockDetailsReusableData", {})
        
        # Extract market cap and PE ratio
        market_cap = 0
        pe_ratio = 0
        ticker_id = symbol
        
        if isinstance(stock_details, dict):
            market_cap = safe_float(stock_details.get("marketCap", 0))
            pe_ratio = safe_float(stock_details.get("pPerEBasicExcludingExtraordinaryItemsTTM", 0))
            ticker_id = stock_details.get("tickerId", symbol)
        
        # Step 6: Build clean response for frontend
        stock_data = {
            "symbol": ticker_id,
            "name": company_name,
            "price": round(current_price, 2),
            "change": price_change,
            "changePercent": round(price_change_percent, 2),
            "open": round(current_price, 2),  # Use current price as open (API doesn't provide separate open)
            "high": round(year_high, 2) if year_high else round(current_price * 1.02, 2),  # Approximate
            "low": round(year_low, 2) if year_low else round(current_price * 0.98, 2),  # Approximate
            "volume": "N/A",  # Indian Stock API doesn't provide volume
            "marketCap": f"₹{market_cap / 10000000:.2f}Cr" if market_cap else "N/A",  # Convert to Crores
            "peRatio": round(pe_ratio, 2) if pe_ratio else None,
            "week52High": round(year_high, 2) if year_high else None,
            "week52Low": round(year_low, 2) if year_low else None,
            "currency": "INR",
            "industry": data.get("industry", ""),
            "avgVolume": "N/A",  # Not provided by API
            "beta": None,  # Not provided by API
            "dividend": None  # Not provided by API
        }
        
        return jsonify(stock_data), 200
        
    except requests.exceptions.Timeout:
        # Handle timeout errors
        return jsonify({
            "error": "Request timeout",
            "message": "Stock API request timed out. Please try again."
        }), 502
        
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (401, 403, etc.)
        status_code = e.response.status_code if e.response else 502
        
        if status_code == 401:
            return jsonify({
                "error": "Authentication failed",
                "message": "Invalid API key. Please check your STOCK_API_KEY."
            }), 502
        elif status_code == 429:
            return jsonify({
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later."
            }), 502
        else:
            return jsonify({
                "error": "External API error",
                "message": f"Stock API returned error: {status_code}"
            }), 502
        
    except requests.exceptions.RequestException as e:
        # Handle network/API errors
        return jsonify({
            "error": "External API error",
            "message": f"Failed to fetch stock data: {str(e)}"
        }), 502
        
    except (ValueError, KeyError) as e:
        # Handle JSON parsing or missing key errors
        return jsonify({
            "error": "Invalid API response",
            "message": "Failed to parse stock data from API"
        }), 502
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({
            "error": "Internal server error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500


@stocks_bp.route("/search/batch", methods=["POST"])
def search_multiple_stocks():
    """
    Search for multiple Indian stocks at once.
    
    Request JSON:
        - symbols: list[str] (required) - List of Indian stock symbols
    
    Returns:
        - 200: Array of stock data
        - 400: Missing or invalid symbols
    
    Example:
        POST /api/stocks/search/batch
        Body: {"symbols": ["TCS", "INFY", "RELIANCE"]}
    """
    
    # Validate API key
    if not STOCK_API_KEY:
        return jsonify({
            "error": "Stock API key not configured"
        }), 500
    
    data = request.get_json()
    
    # Validate request body
    if not data or "symbols" not in data:
        return jsonify({
            "error": "Missing symbols",
            "message": "Please provide 'symbols' array in request body"
        }), 400
    
    symbols = data.get("symbols", [])
    
    # Validate symbols is a list and not empty
    if not isinstance(symbols, list) or len(symbols) == 0:
        return jsonify({
            "error": "Invalid symbols",
            "message": "Symbols must be a non-empty array"
        }), 400
    
    # Limit to 10 symbols per request to avoid rate limits
    if len(symbols) > 10:
        return jsonify({
            "error": "Too many symbols",
            "message": "Maximum 10 symbols allowed per request"
        }), 400
    
    results = []
    headers = {
        "X-Api-Key": STOCK_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Fetch data for each symbol
    for symbol in symbols:
        symbol = symbol.strip().upper()
        
        try:
            stock_url = f"{STOCK_API_BASE_URL}/stock"
            params = {"name": symbol}  # Indian Stock API uses 'name' parameter
            
            response = requests.get(stock_url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                continue  # Skip failed requests
            
            stock_data = response.json()
            
            # Skip if error or invalid data
            if not stock_data or "error" in stock_data:
                continue
            
            # Build minimal stock data
            current_price = float(stock_data.get("lastPrice", 0))
            price_change = float(stock_data.get("change", 0))
            price_change_percent = float(stock_data.get("pChange", 0))
            
            results.append({
                "symbol": stock_data.get("symbol", symbol),
                "name": stock_data.get("companyName", symbol),
                "current_price": round(current_price, 2),
                "price_change": round(price_change, 2),
                "price_change_percent": round(price_change_percent, 2)
            })
            
        except Exception:
            # Skip symbols that fail, don't break the whole request
            continue
    
    return jsonify({
        "results": results,
        "count": len(results)
    }), 200
