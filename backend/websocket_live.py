"""
5paisa WebSocket Live Market Data Stream
Connects to XStream API and streams real-time market data
"""
import json
import time
import websocket
from datetime import datetime


class MarketDataStream:
    """
    WebSocket client for 5paisa live market data streaming.
    """
    
    def __init__(self, token_file="token_store.json"):
        """
        Initialize the market data stream.
        
        Args:
            token_file: Path to the JSON file containing access token and client code
        """
        self.token_file = token_file
        self.access_token = None
        self.client_code = None
        self.ws = None
        self.should_reconnect = True
        self.reconnect_delay = 5  # seconds
        
    def load_credentials(self):
        """
        Load access token and client code from token_store.json.
        """
        try:
            with open(self.token_file, "r") as f:
                data = json.load(f)
            
            self.access_token = data.get("access_token")
            self.client_code = data.get("client_code")
            
            if not self.access_token or not self.client_code:
                raise ValueError("access_token or client_code missing in token_store.json")
            
            print(f"✅ Credentials loaded successfully")
            print(f"👤 Client Code: {self.client_code}")
            
        except FileNotFoundError:
            raise FileNotFoundError(
                f"{self.token_file} not found. Please run 5paisa_auth.py first."
            )
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {self.token_file}")
    
    def get_websocket_url(self):
        """
        Construct the WebSocket URL with authentication parameters.
        
        Returns:
            WebSocket URL string
        """
        return f"wss://openfeed.5paisa.com/feeds/api/chat?Value1={self.access_token}|{self.client_code}"
    
    def on_open(self, ws):
        """
        Callback when WebSocket connection is established.
        """
        print("🔗 WebSocket Connected")
        print("📡 Subscribing to market feed...")
        
        # Prepare subscription message for market data
        # Exch: N = NSE, ExchType: C = Cash, ScripCode: 1660 = Reliance Industries
        subscription_message = {
            "Method": "MarketFeedV3",
            "Operation": "Subscribe",
            "ClientCode": self.client_code,
            "MarketFeedData": [
                {
                    "Exch": "N",
                    "ExchType": "C",
                    "ScripCode": 1660
                }
            ]
        }
        
        # Send subscription request to WebSocket
        try:
            ws.send(json.dumps(subscription_message))
            print("✅ Subscription request sent")
        except Exception as e:
            print(f"❌ Failed to send subscription: {str(e)}")
    
    def on_message(self, ws, message):
        """
        Callback when a message is received from WebSocket.
        
        Args:
            ws: WebSocket instance
            message: Received message (string)
        """
        try:
            # Parse the incoming JSON message
            data = json.loads(message)
            
            # Extract relevant market data fields
            # Note: Field names may vary based on 5paisa API response structure
            if isinstance(data, dict):
                # Extract last traded price (LTP)
                ltp = data.get("LastRate") or data.get("LTP") or data.get("LastTradedPrice")
                
                # Extract timestamp
                timestamp = data.get("Time") or data.get("Timestamp") or datetime.now().strftime("%H:%M:%S")
                
                # Extract scrip/symbol name if available
                symbol = data.get("Symbol") or data.get("ScripName") or "N/A"
                
                # Print market data if LTP is available
                if ltp:
                    print(f"📊 [{timestamp}] {symbol} | LTP: ₹{ltp}")
                else:
                    # Print raw data if structure is different
                    print(f"📦 Received: {json.dumps(data, indent=2)}")
            else:
                print(f"📦 Received: {message}")
                
        except json.JSONDecodeError:
            # Handle non-JSON messages
            print(f"📨 Raw message: {message}")
        except Exception as e:
            print(f"⚠️ Error processing message: {str(e)}")
    
    def on_error(self, ws, error):
        """
        Callback when an error occurs.
        
        Args:
            ws: WebSocket instance
            error: Error object
        """
        print(f"❌ WebSocket Error: {str(error)}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """
        Callback when WebSocket connection is closed.
        
        Args:
            ws: WebSocket instance
            close_status_code: Status code for closure
            close_msg: Close message
        """
        print(f"🔌 WebSocket Closed (Code: {close_status_code})")
        if close_msg:
            print(f"   Message: {close_msg}")
        
        # Attempt reconnection if enabled
        if self.should_reconnect:
            print(f"🔄 Reconnecting in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)
            self.connect()
    
    def connect(self):
        """
        Establish WebSocket connection and start streaming.
        """
        try:
            # Load credentials from token_store.json
            self.load_credentials()
            
            # Get WebSocket URL
            ws_url = self.get_websocket_url()
            
            print(f"🚀 Connecting to 5paisa WebSocket...")
            
            # Create WebSocket connection with callbacks
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start the WebSocket connection (blocking call)
            self.ws.run_forever()
            
        except KeyboardInterrupt:
            print("\n⏹️ Stopping WebSocket stream...")
            self.should_reconnect = False
            if self.ws:
                self.ws.close()
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            
            # Retry connection if enabled
            if self.should_reconnect:
                print(f"🔄 Retrying in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)
                self.connect()
    
    def stop(self):
        """
        Stop the WebSocket connection.
        """
        print("⏹️ Stopping stream...")
        self.should_reconnect = False
        if self.ws:
            self.ws.close()


if __name__ == "__main__":
    print("=" * 60)
    print("5paisa Live Market Data Stream")
    print("=" * 60)
    
    # Create market data stream instance
    stream = MarketDataStream()
    
    try:
        # Start streaming
        stream.connect()
    except KeyboardInterrupt:
        print("\n👋 Stream stopped by user")
        stream.stop()
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        exit(1)
