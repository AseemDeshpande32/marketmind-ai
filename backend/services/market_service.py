"""
Market Service - wraps 5paisa Snapshot and Historical Candles APIs
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

SNAPSHOT_URL = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V1/MarketSnapshot"
# V2 REST GET endpoint — no DNS issues, supports bearer auth
HISTORICAL_BASE = "https://openapi.5paisa.com/V2/historical"
TOKEN_FILE = "token_store.json"

# Interval map: frontend value → 5paisa V2 API value
INTERVAL_MAP = {
    "1m":  "1m",  "1M":  "1m",
    "5m":  "5m",  "5M":  "5m",
    "15m": "15m", "15M": "15m",
    "30m": "30m", "30M": "30m",
    "60m": "60m",
    "1H":  "60m", "1h":  "60m",
    "1d":  "1d",  "1D":  "1d",
    "1w":  "1w",  "1W":  "1w",
}


def _load_credentials() -> Dict[str, str]:
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
        access_token = data.get("access_token")
        client_code  = data.get("client_code")
        if not access_token or not client_code:
            raise ValueError("access_token or client_code missing in token_store.json")
        return {"access_token": access_token, "client_code": client_code}
    except FileNotFoundError:
        raise FileNotFoundError("token_store.json not found. Run 5paisa_auth.py first.")


def get_market_snapshot(scrip_code: int, exchange: str = "N", exchange_type: str = "C") -> Dict[str, Any]:
    """Fetch real-time snapshot for a single stock from 5paisa."""
    credentials = _load_credentials()
    app_key = os.getenv("APP_KEY")
    if not app_key:
        raise ValueError("APP_KEY not found in .env")

    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "head": {"key": app_key},
        "body": {
            "ClientCode": credentials["client_code"],
            "Data": [
                {
                    "Exchange": exchange,
                    "ExchangeType": exchange_type,
                    "ScripCode": scrip_code,
                }
            ],
        },
    }

    response = requests.post(SNAPSHOT_URL, headers=headers, json=payload, timeout=15)
    if response.status_code != 200:
        raise Exception(f"5paisa snapshot API error: {response.status_code} - {response.text}")
    return response.json()


def format_stock_data(api_response: Dict[str, Any], scrip_code: int) -> Optional[Dict[str, Any]]:
    """
    Format the raw 5paisa snapshot response into a clean dict for the frontend.
    Returns None if no data was found.
    """
    try:
        body = api_response.get("body", {})
        data_array = body.get("Data", [])
        if not data_array:
            return None

        d = data_array[0]  # first (and only) item

        def sf(val, default=0.0):
            try:
                return float(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        last_rate  = sf(d.get("LastTradedPrice") or d.get("LastRate"))
        prev_close = sf(d.get("PClose"))
        open_rate  = sf(d.get("Open") or d.get("OpenRate"))
        high       = sf(d.get("High"))
        low        = sf(d.get("Low"))
        volume     = int(sf(d.get("Volume") or d.get("TotalQty"), 0))
        change     = last_rate - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "scripCode":    scrip_code,
            "price":        round(last_rate, 2),
            "prevClose":    round(prev_close, 2),
            "open":         round(open_rate, 2),
            "high":         round(high, 2),
            "low":          round(low, 2),
            "volume":       volume,
            "change":       round(change, 2),
            "changePercent": round(change_pct, 2),
            "upperCircuit": sf(d.get("UpperCircuitLimit") or d.get("UpperLimit")) or None,
            "lowerCircuit": sf(d.get("LowerCircuitLimit") or d.get("LowerLimit")) or None,
            "exchange":     d.get("Exchange", d.get("Exch", "N")),
        }
    except Exception as e:
        print(f"[MARKET] ERROR in format_stock_data: {e}")
        return None


def get_historical_data(
    scrip_code: int,
    exchange: str = "N",
    exchange_type: str = "C",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval: str = "1d",
) -> Dict[str, Any]:
    """
    Fetch historical OHLCV candles from 5paisa V2 REST API.
    GET /V2/historical/{Exch}/{ExchType}/{ScripCode}/{Interval}?from=YYYY-MM-DD&end=YYYY-MM-DD
    """
    credentials = _load_credentials()

    today = datetime.today()
    if not to_date:
        to_date = today.strftime("%Y-%m-%d")
    if not from_date:
        if interval in ("1m", "5m", "15m", "30m"):
            delta = timedelta(days=5)
        elif interval in ("60m", "1H", "1h"):
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=365)
        from_date = (today - delta).strftime("%Y-%m-%d")

    api_interval = INTERVAL_MAP.get(interval, "1d")
    url = f"{HISTORICAL_BASE}/{exchange}/{exchange_type}/{scrip_code}/{api_interval}"

    headers = {
        # V2 endpoint requires lowercase 'bearer'
        "Authorization": f"bearer {credentials['access_token']}",
        "Content-Type": "application/json",
    }
    params = {"from": from_date, "end": to_date}

    print(f"[HIST] GET {url} params={params}")
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"[HIST] status={response.status_code} body={response.text[:300]}")

    if response.status_code == 401:
        raise Exception("Token expired — run 5paisa_auth.py to refresh")
    if response.status_code != 200:
        raise Exception(f"5paisa historical API error: {response.status_code} - {response.text}")
    return response.json()


def format_historical_data(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse V2 historical response.
    V2 format: { "status": "success", "data": { "candles": [[timestamp, O, H, L, C, V], ...] } }
    timestamp is ISO string e.g. "2022-07-15T09:15:00"
    """
    try:
        # V2 REST response
        data = api_response.get("data", {})
        raw_candles = data.get("candles", [])

        # Fallback: old VendorsAPI format
        if not raw_candles:
            body = api_response.get("body", {})
            old_candles = body.get("Data", [])
            result = []
            for c in old_candles:
                dt_str = c.get("DateTime", "")
                try:
                    time_val = int(datetime.fromisoformat(dt_str).timestamp())
                except Exception:
                    time_val = 0
                result.append({
                    "time":   time_val,
                    "open":   float(c.get("Open",   0)),
                    "high":   float(c.get("High",   0)),
                    "low":    float(c.get("Low",    0)),
                    "close":  float(c.get("Close",  0)),
                    "volume": int(float(c.get("Volume", 0))),
                })
            return result

        result = []
        for c in raw_candles:
            # c = ["2022-07-15T09:15:00", open, high, low, close, volume]
            try:
                time_val = int(datetime.fromisoformat(c[0]).timestamp())
            except Exception:
                time_val = 0
            result.append({
                "time":   time_val,
                "open":   float(c[1]),
                "high":   float(c[2]),
                "low":    float(c[3]),
                "close":  float(c[4]),
                "volume": int(float(c[5])) if len(c) > 5 else 0,
            })
        return result

    except Exception as e:
        print(f"[MARKET] ERROR in format_historical_data: {e}")
        return []


# ── Singleton-style module-level instance ────────────────────────────────────
class MarketService:
    """Thin class wrapper so routes can do `from services.market_service import market_service`"""

    def get_market_snapshot(self, scrip_code, exchange="N", exchange_type="C"):
        return get_market_snapshot(scrip_code, exchange, exchange_type)

    def format_stock_data(self, api_response, scrip_code):
        return format_stock_data(api_response, scrip_code)

    def get_historical_data(self, scrip_code, exchange="N", exchange_type="C",
                            from_date=None, to_date=None, interval="1d"):
        return get_historical_data(scrip_code, exchange, exchange_type, from_date, to_date, interval)

    def format_historical_data(self, api_response):
        return format_historical_data(api_response)


market_service = MarketService()
