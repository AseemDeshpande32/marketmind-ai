"""
WebSocket Service for 5paisa Live Market Data
Manages WebSocket connections and broadcasts live data to clients
"""
import json
import time
import threading
import websocket
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv

load_dotenv()


class LiveMarketDataService:
    """Service for streaming live market data via WebSocket"""
    
    def __init__(self):
        self.token_file = "token_store.json"
        self.ws = None
        self.is_connected = False
        self.subscribers = {}  # Dict of scrip_code -> list of callbacks
        self.thread = None
        
    def load_credentials(self) -> Dict[str, str]:
        """Load access token and client code from token_store.json"""
        try:
            with open(self.token_file, "r") as f:
                data = json.load(f)
            
            access_token = data.get("access_token")
            client_code = data.get("client_code")
            
            if not access_token or not client_code:
                raise ValueError("Missing credentials in token_store.json")
            
            print(f"✅ Loaded credentials - Client: {client_code}, Token: {access_token[:20]}...")
            
            return {
                "access_token": access_token,
                "client_code": client_code
            }
        except FileNotFoundError:
            print("❌ token_store.json not found")
            raise FileNotFoundError("token_store.json not found")
        except Exception as e:
            print(f"❌ Error loading credentials: {e}")
            raise
    
    def get_websocket_url(self) -> str:
        """Construct the WebSocket URL"""
        credentials = self.load_credentials()
        access_token = credentials["access_token"]
        client_code = credentials["client_code"]
        
        return f"wss://openfeed.5paisa.com/feeds/api/chat?Value1={access_token}|{client_code}"
    
    def on_open(self, ws):
        """Callback when WebSocket connection opens"""
        self.is_connected = True
        print("✅ 5paisa WebSocket Connected Successfully")
    
    def on_message(self, ws, message):
        """Callback when message is received"""
        try:
            print(f"📥 Received message: {message[:200]}...")  # Print first 200 chars
            data = json.loads(message)
            
            # 5paisa sends data as an array, extract first element
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
                print(f"📦 Extracted data from array: {data}")
            
            # Extract scrip code and broadcast to subscribers
            if isinstance(data, dict):
                # 5paisa uses "Token" field for scrip code, also check "ScripCode" as fallback
                scrip_code = data.get("Token") or data.get("ScripCode")
                print(f"📊 Parsed data for scrip {scrip_code}: LastRate={data.get('LastRate')}, High={data.get('High')}, Low={data.get('Low')}")
                
                if scrip_code and scrip_code in self.subscribers:
                    print(f"📢 Found {len(self.subscribers[scrip_code])} subscribers for scrip {scrip_code}")
                    # Normalize field names for frontend
                    normalized_data = {
                        "ScripCode": scrip_code,
                        "LastTradedPrice": data.get("LastRate"),
                        "LastRate": data.get("LastRate"),
                        "LTP": data.get("LastRate"),
                        "High": data.get("High"),
                        "Low": data.get("Low"),
                        "Volume": data.get("TotalQty"),
                        "OpenRate": data.get("OpenRate"),
                        "PreviousClose": data.get("PClose"),
                        "Change": data.get("Change"),
                        "ChangePercent": data.get("ChgPcnt"),
                        "Time": data.get("Time")
                    }
                    for callback in self.subscribers[scrip_code]:
                        callback(normalized_data)
                    print(f"✅ Broadcast complete for scrip {scrip_code}")
                elif scrip_code:
                    print(f"⚠️ No subscribers found for scrip {scrip_code}")
                else:
                    print(f"⚠️ No scrip code found in data")
            else:
                print(f"⚠️ Data is not a dict after processing: {type(data)}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            import traceback
            traceback.print_exc()
    
    def on_error(self, ws, error):
        """Callback when error occurs"""
        print(f"WebSocket Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Callback when connection closes"""
        self.is_connected = False
        print(f"WebSocket Closed: {close_status_code}")
    
    def subscribe(self, scrip_code: int, exchange: str = "N", 
                  exchange_type: str = "C") -> bool:
        """
        Subscribe to live data for a specific stock
        
        Args:
            scrip_code: Stock scrip code
            exchange: Exchange code
            exchange_type: Exchange type
            
        Returns:
            Success status
        """
        if not self.ws or not self.is_connected:
            print(f"❌ Cannot subscribe - WebSocket not connected")
            return False
        
        credentials = self.load_credentials()
        
        subscription_message = {
            "Method": "MarketFeedV3",
            "Operation": "Subscribe",
            "ClientCode": credentials["client_code"],
            "MarketFeedData": [
                {
                    "Exch": exchange,
                    "ExchType": exchange_type,
                    "ScripCode": scrip_code
                }
            ]
        }
        
        try:
            print(f"📤 Sending subscription: {subscription_message}")
            self.ws.send(json.dumps(subscription_message))
            print(f"✅ Subscription sent for scrip {scrip_code}")
            return True
        except Exception as e:
            print(f"❌ Failed to subscribe: {e}")
            return False
    
    def unsubscribe(self, scrip_code: int, exchange: str = "N", 
                    exchange_type: str = "C") -> bool:
        """Unsubscribe from a stock"""
        if not self.ws or not self.is_connected:
            return False
        
        credentials = self.load_credentials()
        
        unsubscribe_message = {
            "Method": "MarketFeedV3",
            "Operation": "Unsubscribe",
            "ClientCode": credentials["client_code"],
            "MarketFeedData": [
                {
                    "Exch": exchange,
                    "ExchType": exchange_type,
                    "ScripCode": scrip_code
                }
            ]
        }
        
        try:
            self.ws.send(json.dumps(unsubscribe_message))
            return True
        except Exception as e:
            print(f"Failed to unsubscribe: {e}")
            return False
    
    def connect(self):
        """Establish WebSocket connection"""
        if self.is_connected:
            print("⚠️ Already connected to 5paisa WebSocket")
            return
        
        try:
            ws_url = self.get_websocket_url()
            print(f"🔌 Connecting to 5paisa WebSocket...")
            print(f"📍 WebSocket URL: {ws_url[:50]}...")  # Print first 50 chars
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Run in separate thread
            self.thread = threading.Thread(target=self.ws.run_forever)
            self.thread.daemon = True
            self.thread.start()
            
            # Wait for connection
            timeout = 5
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                print("✅ 5paisa WebSocket connection established")
            else:
                print("❌ 5paisa WebSocket connection timeout")
                
        except Exception as e:
            print(f"❌ Error connecting to 5paisa WebSocket: {e}")
            import traceback
            traceback.print_exc()
    
    def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
            self.is_connected = False


# Singleton instance
live_market_service = LiveMarketDataService()
