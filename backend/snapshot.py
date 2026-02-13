"""
5paisa Market Snapshot API Client
Fetches real-time market snapshot data for specific stocks
"""
import os
import json
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_credentials(token_file="token_store.json") -> Dict[str, str]:
    """
    Load access token and client code from token_store.json.
    
    Args:
        token_file: Path to the JSON file containing credentials
        
    Returns:
        Dictionary containing access_token and client_code
        
    Raises:
        FileNotFoundError: If token_store.json doesn't exist
        ValueError: If required credentials are missing
    """
    try:
        with open(token_file, "r") as f:
            data = json.load(f)
        
        access_token = data.get("access_token")
        client_code = data.get("client_code")
        
        if not access_token or not client_code:
            raise ValueError("access_token or client_code missing in token_store.json")
        
        return {
            "access_token": access_token,
            "client_code": client_code
        }
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f"{token_file} not found. Please run 5paisa_auth.py first to generate tokens."
        )
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in {token_file}")


def get_market_snapshot(scrip_code: int) -> Dict[str, Any]:
    """
    Fetch market snapshot data for a specific stock.
    
    Args:
        scrip_code: The scrip code of the stock (e.g., 1660 for Reliance)
        
    Returns:
        Dictionary containing market data
        
    Raises:
        Exception: If API request fails
    """
    # Load credentials from token_store.json
    credentials = load_credentials()
    access_token = credentials["access_token"]
    client_code = credentials["client_code"]
    
    # Load APP_KEY from environment
    app_key = os.getenv("APP_KEY")
    if not app_key:
        raise ValueError("APP_KEY not found in .env file")
    
    # Define the API endpoint
    api_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V1/MarketSnapshot"
    
    # Set up request headers with Bearer token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Prepare the JSON payload
    # Exchange: N = NSE, ExchangeType: C = Cash
    # head.key should contain APP_KEY (not access_token)
    payload = {
        "head": {
            "key": app_key
        },
        "body": {
            "ClientCode": client_code,
            "Data": [
                {
                    "Exchange": "N",
                    "ExchangeType": "C",
                    "ScripCode": scrip_code
                }
            ]
        }
    }
    
    print(f"📡 Fetching market snapshot for ScripCode: {scrip_code}...")
    
    # Send POST request to the API
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to 5paisa API: {str(e)}")
    
    # Check if request was successful
    if response.status_code != 200:
        raise Exception(
            f"API request failed with status code {response.status_code}. "
            f"Response: {response.text}"
        )
    
    # Parse the JSON response
    try:
        response_data = response.json()
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON response from API: {response.text}")
    
    # Check for API-level errors in response body
    # Status: -1 = Error, Status: 0 or 1 = Success
    body = response_data.get("body", {})
    if body.get("Status") == -1:
        error_message = body.get("Message", "Unknown error")
        raise Exception(
            f"API returned error: {error_message}. "
            f"This might indicate: 1) Expired access token (run 5paisa_auth.py), "
            f"2) Invalid scrip code, or 3) Market is closed."
        )
    
    return response_data


def display_market_data(data: Dict[str, Any], scrip_code: int):
    """
    Display formatted market data.
    
    Args:
        data: Response data from API
        scrip_code: The scrip code of the stock
    """
    try:
        # Extract market data from response body
        body = data.get("body", {})
        
        # Check if Data array exists and has items
        data_array = body.get("Data", [])
        if not data_array or len(data_array) == 0:
            print("\n⚠️ No market data available in response")
            print(json.dumps(data, indent=2))
            return
        
        # Get the first item from Data array
        market_data = data_array[0]
        
        # Extract key market metrics
        last_price = market_data.get("LastTradedPrice") or market_data.get("LastRate") or market_data.get("LTP")
        open_price = market_data.get("Open") or market_data.get("OpenRate")
        high_price = market_data.get("High") or market_data.get("HighRate")
        low_price = market_data.get("Low") or market_data.get("LowRate")
        year_high = market_data.get("AHigh") or market_data.get("YearHigh") or market_data.get("High52Week")
        year_low = market_data.get("ALow") or market_data.get("YearLow") or market_data.get("Low52Week")
        volume = market_data.get("Volume") or market_data.get("TotalQty")
        symbol = market_data.get("Symbol") or market_data.get("ScripName") or f"ScripCode {scrip_code}"
        net_change = market_data.get("NetChange")
        prev_close = market_data.get("PClose")
        
        # Display formatted market snapshot
        print("\n" + "=" * 60)
        print(f"📊 Market Snapshot: {symbol}")
        print("=" * 60)
        
        if last_price:
            print(f"💰 Last Traded Price: ₹{last_price}")
        if prev_close:
            print(f"📌 Previous Close:    ₹{prev_close}")
        if net_change:
            change_icon = "📈" if float(net_change) >= 0 else "📉"
            print(f"{change_icon} Net Change:        ₹{net_change}")
        if open_price:
            print(f"🔓 Open:              ₹{open_price}")
        if high_price:
            print(f"⬆️  High:              ₹{high_price}")
        if low_price:
            print(f"⬇️  Low:               ₹{low_price}")
        if year_high:
            print(f"📈 52-Week High:      ₹{year_high}")
        if year_low:
            print(f"📉 52-Week Low:       ₹{year_low}")
        if volume:
            # Convert volume to integer for comma formatting
            try:
                volume_int = int(float(volume))
                print(f"📊 Volume:            {volume_int:,}")
            except (ValueError, TypeError):
                print(f"📊 Volume:            {volume}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"⚠️ Error displaying data: {str(e)}")
        print("\n📦 Raw API Response:")
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    try:
        # Example: Fetch market snapshot for Reliance Industries (ScripCode: 1660)
        # You can change this to any valid scrip code
        scrip_code = 1660
        
        # Get market snapshot data
        market_data = get_market_snapshot(scrip_code)
        
        # Display the formatted data
        display_market_data(market_data, scrip_code)
        
        print("\n✅ Market snapshot retrieved successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        exit(1)
