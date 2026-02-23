"""
Stock Search API Blueprint for MarketMind AI
Handles real-time stock data fetching from 5paisa API
"""

import os
import sys
from flask import Blueprint, request, jsonify

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_service import market_service
from services.script_master_service import script_master_service

# Create stocks blueprint with /api/stocks prefix
stocks_bp = Blueprint("stocks", __name__, url_prefix="/api/stocks")


def _safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _snapshot_to_dict(symbol, scrip_code, market_data, exchange="NSE"):
    last_rate  = _safe_float(market_data.get("LastTradedPrice") or market_data.get("LastRate"))
    open_rate  = _safe_float(market_data.get("Open") or market_data.get("OpenRate"))
    high       = _safe_float(market_data.get("High"))
    low        = _safe_float(market_data.get("Low"))
    prev_close = _safe_float(market_data.get("PClose"))
    volume     = _safe_float(market_data.get("Volume") or market_data.get("TotalQty"), 0)
    price_change = last_rate - prev_close
    pct = (price_change / prev_close * 100) if prev_close else 0
    return {
        "symbol":        symbol,
        "name":          market_data.get("Name", symbol),
        "scripCode":     scrip_code,
        "price":         round(last_rate, 2),
        "change":        round(price_change, 2),
        "changePercent": round(pct, 2),
        "open":          round(open_rate, 2),
        "high":          round(high, 2),
        "low":           round(low, 2),
        "prevClose":     round(prev_close, 2),
        "volume":        int(volume),
        "exchange":      exchange,
        "currency":      "INR",
        "lastUpdated":   market_data.get("LastUpdateTime", ""),
    }


# ─── /search ─────────────────────────────────────────────────────────────────

@stocks_bp.route("/search", methods=["GET"])
def search_stock():
    """GET /api/stocks/search?symbol=TCS&exchange=N"""
    symbol   = request.args.get("symbol", "").strip().upper()
    exchange = request.args.get("exchange", "N").strip().upper()

    if not symbol:
        return jsonify({"error": "Missing stock symbol"}), 400

    try:
        exch_str   = "NSE" if exchange in ("N", "NSE") else "BSE"
        exch_code  = "N" if exch_str == "NSE" else "B"
        exch_type  = "C"

        scrip_code = script_master_service.get_scrip_code(symbol, exch_code)
        if not scrip_code:
            return jsonify({"error": "Stock not found",
                            "message": f"'{symbol}' not found in scripmaster. "
                                       "Ensure backend/data/scripmaster-csv-format.csv exists."}), 404

        snap = market_service.get_market_snapshot(scrip_code, exch_code, exch_type)
        data_arr = (snap.get("body") or snap).get("Data", [])
        if not data_arr:
            return jsonify({"error": "No market data", "message": f"No data for {symbol}"}), 404

        return jsonify(_snapshot_to_dict(symbol, scrip_code, data_arr[0], exch_str)), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


# ─── /search/batch ───────────────────────────────────────────────────────────

@stocks_bp.route("/search/batch", methods=["POST"])
def search_multiple_stocks():
    """POST /api/stocks/search/batch  Body: {"symbols": ["TCS","INFY"]}"""
    body = request.get_json()
    if not body or "symbols" not in body:
        return jsonify({"error": "Missing symbols"}), 400

    symbols = body["symbols"]
    if not isinstance(symbols, list) or not symbols:
        return jsonify({"error": "Symbols must be a non-empty array"}), 400
    if len(symbols) > 10:
        return jsonify({"error": "Maximum 10 symbols per request"}), 400

    results = []
    for sym in symbols:
        sym = sym.strip().upper()
        try:
            sc = script_master_service.get_scrip_code(sym, "N")
            if not sc:
                continue
            snap = market_service.get_market_snapshot(sc, "N", "C")
            data_arr = (snap.get("body") or snap).get("Data", [])
            if not data_arr:
                continue
            d = data_arr[0]
            lp = _safe_float(d.get("LastTradedPrice") or d.get("LastRate"))
            pc = _safe_float(d.get("PClose"))
            ch = lp - pc
            results.append({
                "symbol":             sym,
                "name":               d.get("Name", sym),
                "current_price":      round(lp, 2),
                "price_change":       round(ch, 2),
                "price_change_percent": round((ch / pc * 100) if pc else 0, 2),
            })
        except Exception as e:
            print(f"[BATCH] failed for {sym}: {e}")
    return jsonify({"results": results, "count": len(results)}), 200


# ─── /5paisa/snapshot/<scrip_code> ───────────────────────────────────────────

@stocks_bp.route("/5paisa/snapshot/<int:scrip_code>", methods=["GET"])
def get_5paisa_snapshot(scrip_code):
    """GET /api/stocks/5paisa/snapshot/2885?exchange=N&exchange_type=C"""
    exchange      = request.args.get("exchange", "N")
    exchange_type = request.args.get("exchange_type", "C")
    try:
        snap = market_service.get_market_snapshot(scrip_code, exchange, exchange_type)
        formatted = market_service.format_stock_data(snap)
        if not formatted:
            return jsonify({"error": "No data"}), 404
        return jsonify(formatted), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── /5paisa/search ──────────────────────────────────────────────────────────

@stocks_bp.route("/5paisa/search", methods=["GET"])
def search_5paisa():
    """GET /api/stocks/5paisa/search?q=RELI&exchange=N"""
    query    = request.args.get("q", "").strip()
    exchange = request.args.get("exchange", "N")
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    try:
        matches = script_master_service.search_stock(query, exchange, "C")
        return jsonify({"results": matches, "count": len(matches)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── /search-scripcode ───────────────────────────────────────────────────────

@stocks_bp.route("/search-scripcode", methods=["GET"])
def search_scripcode():
    """GET /api/stocks/search-scripcode?symbol=TCS&exchange=N"""
    symbol   = request.args.get("symbol", "").strip().upper()
    exchange = request.args.get("exchange", "N")
    if not symbol:
        return jsonify({"error": "Missing symbol"}), 400
    try:
        sc = script_master_service.get_scrip_code(symbol, exchange)
        if not sc:
            return jsonify({"error": "Not found"}), 404
        details = script_master_service.get_stock_details(sc) or {}
        return jsonify({"scripCode": sc, "symbol": symbol, **details}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── /get-stock-by-name/<symbol> ─────────────────────────────────────────────

@stocks_bp.route("/get-stock-by-name/<symbol>", methods=["GET"])
def get_stock_by_name(symbol):
    """GET /api/stocks/get-stock-by-name/TCS?exchange=N"""
    symbol   = symbol.strip().upper()
    exchange = request.args.get("exchange", "N").strip().upper()
    exch_code = "N" if exchange in ("N", "NSE") else "B"
    exch_str  = "NSE" if exch_code == "N" else "BSE"

    try:
        sc = script_master_service.get_scrip_code(symbol, exch_code)
        if not sc:
            return jsonify({"error": "Stock not found",
                            "message": f"'{symbol}' not found in scripmaster."}), 404

        snap = market_service.get_market_snapshot(sc, exch_code, "C")
        data_arr = (snap.get("body") or snap).get("Data", [])
        if not data_arr:
            return jsonify({"error": "No market data"}), 404

        return jsonify(_snapshot_to_dict(symbol, sc, data_arr[0], exch_str)), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── /5paisa/historical/<scrip_code> ─────────────────────────────────────────

@stocks_bp.route("/5paisa/historical/<int:scrip_code>", methods=["GET"])
def get_5paisa_historical(scrip_code):
    """GET /api/stocks/5paisa/historical/2885?exchange=N&exchange_type=C&interval=1D"""
    exchange      = request.args.get("exchange", "N")
    exchange_type = request.args.get("exchange_type", "C")
    interval      = request.args.get("interval", "1D")
    from_date     = request.args.get("from", "")
    to_date       = request.args.get("to", "")

    try:
        raw     = market_service.get_historical_data(
            scrip_code,
            exchange=exchange,
            exchange_type=exchange_type,
            interval=interval,
            from_date=from_date or None,
            to_date=to_date or None,
        )
        candles = market_service.format_historical_data(raw)
        return jsonify({"scripCode": scrip_code, "interval": interval,
                        "candles": candles, "count": len(candles)}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
