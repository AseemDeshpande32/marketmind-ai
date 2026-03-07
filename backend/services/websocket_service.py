"""
WebSocket Service
Manages 5paisa real-time price feed and broadcasts via Flask-SocketIO.
"""
import json
import logging
import threading
import time
import websocket
from typing import Dict, Optional

log = logging.getLogger("ws_service")
logging.basicConfig(level=logging.INFO)


class WebSocketService:
    """
    - Connects once to the 5paisa XStream WebSocket feed.
    - Keeps track of which scrip codes the frontend wants.
    - Broadcasts `stock_update` events over Flask-SocketIO.
    """

    FEED_URL_TPL = "wss://openfeed.5paisa.com/feeds/api/chat?Value1={token}|{code}"

    def __init__(self):
        self.socketio = None           # set by init_app()
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.subscriptions: Dict[int, dict] = {}   # scrip_code → meta
        self.access_token: Optional[str] = None
        self.client_code: Optional[str] = None
        self._connected = False
        self._stop = False

    # ── init ──────────────────────────────────────────────────────────────────

    def init_app(self, socketio, token_file="token_store.json"):
        """Call once at startup to wire up the SocketIO instance."""
        self.socketio = socketio
        try:
            with open(token_file) as f:
                data = json.load(f)
            self.access_token = data.get("access_token")
            self.client_code  = data.get("client_code")
            log.info("[WS] Credentials loaded OK for client %s", self.client_code)
        except Exception as e:
            log.warning("[WS] Could not load credentials: %s", e)

    # ── subscribe / unsubscribe ───────────────────────────────────────────────

    def subscribe(self, scrip_code: int, exchange: str = "N", exchange_type: str = "C"):
        with self.lock:
            self.subscriptions[scrip_code] = {
                "Exch": exchange,
                "ExchType": exchange_type,
                "ScripCode": scrip_code,
            }
        if self._connected and self.ws:
            self._send_subscribe([scrip_code])
        elif not self._connected:
            self._ensure_connected()

    def unsubscribe(self, scrip_code: int):
        with self.lock:
            self.subscriptions.pop(scrip_code, None)
        if self._connected and self.ws:
            self._send_unsubscribe([scrip_code])

    # ── internal WebSocket plumbing ───────────────────────────────────────────

    def _ensure_connected(self):
        if self.thread and self.thread.is_alive():
            return
        if not self.access_token:
            log.warning("[WS] No credentials, skipping connect")
            return
        self._stop = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        url = self.FEED_URL_TPL.format(
            token=self.access_token, code=self.client_code
        )
        while not self._stop:
            try:
                self.ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                log.error("[WS] Run loop error: %s", e)
            if not self._stop:
                log.info("[WS] Reconnecting in 5s...")
                time.sleep(5)

    def _on_open(self, ws):
        self._connected = True
        log.info("[WS] 5paisa feed CONNECTED")
        keys = list(self.subscriptions.keys())
        if keys:
            self._send_subscribe(keys)
        else:
            log.info("[WS] Connected but no subscriptions yet")

    def _on_close(self, ws, code, msg):
        self._connected = False
        log.info("[WS] 5paisa feed closed (%s)", code)

    def _on_error(self, ws, error):
        log.error("[WS] ERROR: %s", error)

    def _on_message(self, ws, raw):
        try:
            # Log first raw message so we can verify format
            if not hasattr(self, '_msg_count'):
                self._msg_count = 0
            self._msg_count += 1
            if self._msg_count <= 5:
                log.info("[WS] RAW MSG #%d: %s", self._msg_count, raw[:400])

            data = json.loads(raw)
            # 5paisa sometimes sends a list
            if isinstance(data, list):
                for item in data:
                    self._process_tick(item)
            elif isinstance(data, dict):
                self._process_tick(data)
        except Exception as e:
            log.error("[WS] Message parse error: %s", e)

    def _process_tick(self, data: dict):
        # 5paisa uses different field names depending on feed version
        scrip_code = (
            data.get("Token") or data.get("ScripCode") or
            data.get("Scripcode") or data.get("scripcode") or
            data.get("scripCode")
        )
        if not scrip_code:
            return
        scrip_code = int(scrip_code)

        # WS feed uses LastRate; snapshot uses LastTradedPrice
        price = (
            data.get("LastRate") or data.get("LastTradedPrice") or
            data.get("LTP") or data.get("ltp")
        )
        if not price:
            return

        pclose = float(data.get("PClose", 0) or data.get("PrevClose", 0) or 0)
        ltp    = float(price)

        payload = {
            "scrip_code":      scrip_code,
            "LastTradedPrice": ltp,
            "High":   float(data.get("High",  0) or 0),
            "Low":    float(data.get("Low",   0) or 0),
            "Volume": int(float(data.get("Volume", 0) or data.get("TotalQty", 0) or 0)),
            "PClose": pclose,
            "Change":        round(ltp - pclose, 2),
            "ChangePercent": round((ltp - pclose) / pclose * 100 if pclose else 0, 2),
        }

        if self.socketio:
            self.socketio.emit("stock_update", payload, namespace="/")

    # ── subscription messages ─────────────────────────────────────────────────

    def _send_subscribe(self, scrip_codes):
        with self.lock:
            feed_data = [
                self.subscriptions[sc]
                for sc in scrip_codes
                if sc in self.subscriptions
            ]
        if not feed_data:
            return
        msg = {
            "Method":        "MarketFeedV3",
            "Operation":     "Subscribe",
            "ClientCode":    self.client_code,
            "MarketFeedData": feed_data,
        }
        try:
            self.ws.send(json.dumps(msg))
            log.info("[WS] Subscribed: %s", [d['ScripCode'] for d in feed_data])
        except Exception as e:
            log.error("[WS] Subscribe send error: %s", e)

    def _send_unsubscribe(self, scrip_codes):
        feed_data = [{"ScripCode": sc} for sc in scrip_codes]
        msg = {
            "Method":        "MarketFeedV3",
            "Operation":     "Unsubscribe",
            "ClientCode":    self.client_code,
            "MarketFeedData": feed_data,
        }
        try:
            self.ws.send(json.dumps(msg))
        except Exception:
            pass


websocket_service = WebSocketService()
