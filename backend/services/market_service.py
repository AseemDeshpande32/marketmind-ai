"""
5paisa Market Data Service
Provides market snapshot and live data functionality
"""
import os
import json
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class MarketDataService:
    """Service class for 5paisa market data operations"""
    
    def __init__(self):
        self.token_file = "token_store.json"
        self.api_base_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc"
        self.app_key = os.getenv("APP_KEY")
        
    def load_credentials(self) -> Dict[str, str]:
        """Load access token and client code from token_store.json"""
        try:
            with open(self.token_file, "r") as f:
                data = json.load(f)
            
            access_token = data.get("access_token")
            client_code = data.get("client_code")
            
            if not access_token or not client_code:
                raise ValueError("Missing credentials in token_store.json")
            
            return {
                "access_token": access_token,
                "client_code": client_code
            }
        except FileNotFoundError:
            raise FileNotFoundError("token_store.json not found. Run 5paisa_auth.py first")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in token_store.json")
    
    def get_market_snapshot(self, scrip_code: int, exchange: str = "N", 
                           exchange_type: str = "C") -> Dict[str, Any]:
        """
        Fetch market snapshot for a specific stock
        
        Args:
            scrip_code: Stock scrip code (e.g., 1660 for Reliance)
            exchange: Exchange code (N=NSE, B=BSE)
            exchange_type: Type (C=Cash, D=Derivative)
            
        Returns:
            Dictionary with market data
        """
        # Load credentials
        credentials = self.load_credentials()
        access_token = credentials["access_token"]
        client_code = credentials["client_code"]
        
        if not self.app_key:
            raise ValueError("APP_KEY not found in environment")
        
        # Prepare request
        api_url = f"{self.api_base_url}/V1/MarketSnapshot"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "head": {
                "key": self.app_key
            },
            "body": {
                "ClientCode": client_code,
                "Data": [
                    {
                        "Exchange": exchange,
                        "ExchangeType": exchange_type,
                        "ScripCode": scrip_code
                    }
                ]
            }
        }
        
        # Make request
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to 5paisa API: {str(e)}")
        
        if response.status_code != 200:
            raise Exception(f"API error (status {response.status_code}): {response.text}")
        
        # Parse response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {response.text}")
        
        # Check for API errors
        body = response_data.get("body", {})
        if body.get("Status") == -1:
            error_msg = body.get("Message", "Unknown error")
            raise Exception(f"API error: {error_msg}")
        
        return response_data
    
    def format_stock_data(self, api_response: Dict[str, Any], scrip_code: int) -> Optional[Dict[str, Any]]:
        """
        Format 5paisa API response to match frontend expectations
        
        Args:
            api_response: Raw API response from get_market_snapshot
            scrip_code: Stock scrip code
            
        Returns:
            Formatted stock data dictionary
        """
        try:
            body = api_response.get("body", {})
            data_array = body.get("Data", [])
            
            if not data_array:
                return None
            
            market_data = data_array[0]
            
            # Extract values
            last_price = float(market_data.get("LastTradedPrice", 0))
            open_price = float(market_data.get("Open", 0))
            high_price = float(market_data.get("High", 0))
            low_price = float(market_data.get("Low", 0))
            prev_close = float(market_data.get("PClose", 0))
            net_change = float(market_data.get("NetChange", 0))
            volume = market_data.get("Volume", "0")
            year_high = float(market_data.get("AHigh", 0))
            year_low = float(market_data.get("ALow", 0))
            
            # Calculate change percentage
            change_percent = (net_change / prev_close * 100) if prev_close else 0
            
            # Convert volume to integer
            try:
                volume_int = int(float(volume))
            except (ValueError, TypeError):
                volume_int = 0
            
            # Format response
            return {
                "symbol": str(scrip_code),
                "name": f"ScripCode {scrip_code}",  # Can be enhanced with scrip name mapping
                "price": round(last_price, 2),
                "change": round(net_change, 2),
                "changePercent": round(change_percent, 2),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "volume": volume_int,
                "prevClose": round(prev_close, 2),
                "week52High": round(year_high, 2),
                "week52Low": round(year_low, 2),
                "currency": "INR",
                "exchange": market_data.get("Exchange", "N"),
                "exchangeType": market_data.get("ExchangeType", "C"),
                "upperCircuit": float(market_data.get("UpperCircuitLimit", 0)),
                "lowerCircuit": float(market_data.get("LowerCircuitLimit", 0))
            }
            
        except Exception as e:
            raise Exception(f"Error formatting data: {str(e)}")
    
    def get_historical_data(self, scrip_code: int, exchange: str = "N",
                           exchange_type: str = "C", from_date: str = None,
                           to_date: str = None, interval: str = "1d") -> Dict[str, Any]:
        """
        Fetch historical candle data using the 5paisa V2 REST API.
        
        Endpoint: GET https://openapi.5paisa.com/V2/historical/{Exch}/{ExchType}/{ScripCode}/{Interval}
                       ?from={FromDate}&end={EndDate}
        
        Args:
            scrip_code:    Stock scrip code (e.g., 2885 for Reliance)
            exchange:      Exchange code  — N (NSE) or B (BSE)
            exchange_type: Exchange type  — C (Cash) or D (Derivatives)
            from_date:     Start date YYYY-MM-DD  (defaults based on interval)
            to_date:       End date   YYYY-MM-DD  (defaults to today)
            interval:      Candle interval — 1m, 5m, 10m, 15m, 30m, 60m, 1d
        """
        from datetime import datetime, timedelta

        # Normalise interval value coming from frontend (e.g. "60" -> "60m", "D" -> "1d")
        interval_map = {
            "1": "1m", "5": "5m", "10": "10m", "15": "15m",
            "30": "30m", "60": "60m", "D": "1d", "1d": "1d",
            "1m": "1m", "5m": "5m", "10m": "10m", "15m": "15m",
            "30m": "30m", "60m": "60m",
        }
        api_interval = interval_map.get(interval, "1d")

        # Smart default date ranges based on interval
        today = datetime.now()
        if not to_date:
            to_dt = today
        else:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")

        if not from_date:
            if api_interval == "1m":
                from_dt = to_dt - timedelta(days=5)
            elif api_interval in ("5m", "10m", "15m"):
                from_dt = to_dt - timedelta(days=30)
            elif api_interval in ("30m", "60m"):
                from_dt = to_dt - timedelta(days=90)
            else:  # 1d
                from_dt = to_dt - timedelta(days=180)
        else:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")

        from_str = from_dt.strftime("%Y-%m-%d")
        to_str   = to_dt.strftime("%Y-%m-%d")

        # Load credentials
        credentials = self.load_credentials()
        access_token = credentials["access_token"]

        # Build URL:  /V2/historical/{Exch}/{ExchType}/{ScripCode}/{Interval}
        api_url = (
            f"https://openapi.5paisa.com/V2/historical"
            f"/{exchange}/{exchange_type}/{scrip_code}/{api_interval}"
            f"?from={from_str}&end={to_str}"
        )

        headers = {
            "Authorization": f"bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(api_url, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to 5paisa API: {str(e)}")

        if response.status_code == 401:
            raise FileNotFoundError("Invalid or expired access token")
        if response.status_code != 200:
            raise Exception(f"API error (status {response.status_code}): {response.text[:300]}")

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {response.text[:300]}")

        # Failure response has head.Status == 1
        head = response_data.get("head", {})
        if head.get("Status") == 1:
            raise Exception(f"5paisa API error: {head.get('Status_description', 'Unknown error')}")

        return response_data

    def format_historical_data(self, api_response: Dict[str, Any]) -> list:
        """
        Format 5paisa V2 historical response for charting.
        API returns candles as arrays: [timestamp, open, high, low, close, volume]
        """
        try:
            data = api_response.get("data", {})
            candles_raw = data.get("candles", [])

            if not candles_raw:
                return []

            formatted = []
            for c in candles_raw:
                # c = ["2022-07-15T00:00:00", open, high, low, close, volume]
                timestamp = c[0]  # ISO string e.g. "2022-07-15T09:15:00"
                formatted.append({
                    "time":   timestamp,        # keep ISO — frontend converts as needed
                    "open":   float(c[1]),
                    "high":   float(c[2]),
                    "low":    float(c[3]),
                    "close":  float(c[4]),
                    "volume": int(c[5]) if len(c) > 5 else 0,
                })

            # Ensure ascending order
            formatted.sort(key=lambda x: x["time"])
            return formatted

        except Exception as e:
            raise Exception(f"Error formatting historical data: {str(e)}")


# Singleton instance
market_service = MarketDataService()
