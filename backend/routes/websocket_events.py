"""
WebSocket Event Handlers
Handles Socket.IO events from the frontend.
"""
import logging
from flask_socketio import emit
from services.websocket_service import websocket_service

log = logging.getLogger("ws_events")


def register_events(socketio):
    @socketio.on("connect")
    def handle_connect():
        log.info("[SIO] Client connected")
        emit("connected", {"status": "ok"})

    @socketio.on("disconnect")
    def handle_disconnect():
        log.info("[SIO] Client disconnected")

    @socketio.on("subscribe_stock")
    def handle_subscribe(data):
        scrip_code    = int(data.get("scrip_code", 0))
        exchange      = data.get("exchange", "N")
        exchange_type = data.get("exchange_type", "C")
        log.info("[SIO] subscribe_stock: scrip=%s exch=%s", scrip_code, exchange)
        if scrip_code:
            websocket_service.subscribe(scrip_code, exchange, exchange_type)
            emit("subscribed", {"scrip_code": scrip_code})

    @socketio.on("unsubscribe_stock")
    def handle_unsubscribe(data):
        scrip_code = int(data.get("scrip_code", 0))
        if scrip_code:
            websocket_service.unsubscribe(scrip_code)
            emit("unsubscribed", {"scrip_code": scrip_code})
