"""
WebSocket Event Handlers for Real-Time Market Data
"""
from flask_socketio import emit, join_room, leave_room
from services.websocket_service import live_market_service


def register_websocket_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print('Client connected')
        emit('connection_response', {'status': 'Connected to MarketMind'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print('Client disconnected')
    
    @socketio.on('subscribe_stock')
    def handle_subscribe(data):
        """
        Subscribe to live stock data
        
        Args:
            data: {
                'scrip_code': int,
                'exchange': str (optional),
                'exchange_type': str (optional)
            }
        """
        try:
            scrip_code = data.get('scrip_code')
            exchange = data.get('exchange', 'N')
            exchange_type = data.get('exchange_type', 'C')
            
            if not scrip_code:
                emit('error', {'message': 'Missing scrip_code'})
                return
            
            # Join room for this stock
            room_name = f"stock_{scrip_code}"
            join_room(room_name)
            
            print(f"📡 Client joined room: {room_name}")
            
            # Connect to 5paisa WebSocket if not connected
            if not live_market_service.is_connected:
                print("🔌 Connecting to 5paisa WebSocket...")
                live_market_service.connect()
            else:
                print("✅ Already connected to 5paisa WebSocket")
            
            # Subscribe to stock updates
            def broadcast_update(market_data):
                """Callback to broadcast updates to room"""
                print(f"📢 Broadcasting update to room {room_name}: {market_data}")
                socketio.emit('stock_update', market_data, room=room_name)
            
            # Register callback
            if scrip_code not in live_market_service.subscribers:
                live_market_service.subscribers[scrip_code] = []
            live_market_service.subscribers[scrip_code].append(broadcast_update)
            
            print(f"📝 Registered callback for scrip {scrip_code}")
            
            # Subscribe via 5paisa WebSocket
            success = live_market_service.subscribe(scrip_code, exchange, exchange_type)
            print(f"5paisa subscription result: {success}")
            
            if success:
                emit('subscribed', {
                    'scrip_code': scrip_code,
                    'exchange': exchange,
                    'message': 'Successfully subscribed to live updates'
                })
            else:
                emit('error', {'message': 'Failed to subscribe'})
                
        except Exception as e:
            emit('error', {'message': str(e)})
    
    @socketio.on('unsubscribe_stock')
    def handle_unsubscribe(data):
        """
        Unsubscribe from live stock data
        
        Args:
            data: {
                'scrip_code': int,
                'exchange': str (optional),
                'exchange_type': str (optional)
            }
        """
        try:
            scrip_code = data.get('scrip_code')
            exchange = data.get('exchange', 'N')
            exchange_type = data.get('exchange_type', 'C')
            
            if not scrip_code:
                emit('error', {'message': 'Missing scrip_code'})
                return
            
            # Leave room
            room_name = f"stock_{scrip_code}"
            leave_room(room_name)
            
            # Clear subscribers for this scrip
            if scrip_code in live_market_service.subscribers:
                live_market_service.subscribers[scrip_code] = []
            
            # Unsubscribe from 5paisa
            live_market_service.unsubscribe(scrip_code, exchange, exchange_type)
            
            emit('unsubscribed', {
                'scrip_code': scrip_code,
                'message': 'Successfully unsubscribed'
            })
            
        except Exception as e:
            emit('error', {'message': str(e)})
