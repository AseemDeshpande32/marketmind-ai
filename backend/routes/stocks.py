"""
Stock Search API Blueprint for MarketMind AI
Handles real-time stock data fetching from 5paisa API
"""

import os
import sys
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_service import market_service
from services.script_master_service import script_master_service
from services.fundamentals_service import fundamentals_service
from app import db
from models import Watchlist

# Create stocks blueprint with /api/stocks prefix
stocks_bp = Blueprint("stocks", __name__, url_prefix="/api/stocks")


def _safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _snapshot_to_dict(symbol, scrip_code, market_data, exchange="NSE", exchange_code="N", exchange_type="C"):
    last_rate  = _safe_float(market_data.get("LastTradedPrice") or market_data.get("LastRate"))
    open_rate  = _safe_float(market_data.get("Open") or market_data.get("OpenRate"))
    high       = _safe_float(market_data.get("High"))
    low        = _safe_float(market_data.get("Low"))
    prev_close = _safe_float(market_data.get("PClose"))
    volume     = _safe_float(market_data.get("Volume") or market_data.get("TotalQty"), 0)
    if volume <= 0:
        fallback_volume = market_service.get_alphavantage_eod_volume(scrip_code, exchange_code)
        if fallback_volume is not None:
            volume = fallback_volume
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
        formatted = market_service.format_stock_data(snap, scrip_code, exchange, exchange_type)
        if not formatted:
            return jsonify({"error": "No data"}), 404
        return jsonify(formatted), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── /5paisa/search ──────────────────────────────────────────────────────────

@stocks_bp.route("/5paisa/search", methods=["GET"])
def search_5paisa():
    """GET /api/stocks/5paisa/search?q=RELI&exchange=N
    Returns equity stocks (EQ/BE series) and indices only — no ETFs or commodities.
    """
    query    = request.args.get("q", "").strip()
    exchange = request.args.get("exchange", "N")
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    try:
        from services.script_master_service import EQUITY_SERIES

        # Equity stocks — ExchType C, restricted to plain equity series
        equity_matches = script_master_service.search_stock(
            query, exchange,
            exchange_type="C",
            allowed_series=EQUITY_SERIES,
            limit=10,
        )

        # Indices — ExchType C, ScripCode >= 999900000 (5paisa index range), no ETF/FnO
        index_matches = script_master_service.search_stock(
            query, exchange,
            exchange_type="C",
            allowed_series=None,
            no_expiry=True,
            indices_only=True,
            limit=5,
        )

        # Indices first, then equities (deduplicated by scripCode)
        seen_codes = set()
        combined   = []
        for m in index_matches + equity_matches:
            if m['scripCode'] not in seen_codes:
                seen_codes.add(m['scripCode'])
                combined.append(m)

        return jsonify({"results": combined, "count": len(combined)}), 200
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

        return jsonify(_snapshot_to_dict(symbol, sc, data_arr[0], exch_str, exch_code, "C")), 200

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


# ─── /fundamentals ──────────────────────────────────────────────────────────

@stocks_bp.route("/fundamentals", methods=["GET"])
def get_fundamentals():
    """GET /api/stocks/fundamentals?symbol=TCS&exchange=N
    Returns fundamental metrics: P/E, EPS, Book Value, Market Cap
    """
    symbol   = request.args.get("symbol", "").strip().upper()
    exchange = request.args.get("exchange", "N").strip().upper()

    if not symbol:
        return jsonify({"error": "Missing stock symbol"}), 400

    try:
        exch_code = "N" if exchange in ("N", "NSE") else "B"
        result = fundamentals_service.get_fundamentals(symbol, exch_code)
        
        if result.get("error"):
            return jsonify(result), 404
        
        return jsonify(result), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── /trending ──────────────────────────────────────────────────────────────

# Nifty 50 pool — representative large-cap NSE stocks
_NIFTY_POOL = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "HINDUNILVR", "BAJFINANCE", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "WIPRO", "HCLTECH", "AXISBANK", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO", "NESTLEIND",
]

@stocks_bp.route("/trending", methods=["GET"])
def get_trending_stocks():
    """GET /api/stocks/trending?limit=4
    Returns the most active stocks from the Nifty pool sorted by volume.
    Falls back to sort by highest absolute % change if volumes are zero.
    """
    try:
        limit = min(int(request.args.get("limit", 4)), 10)
    except (ValueError, TypeError):
        limit = 4

    results = []
    for sym in _NIFTY_POOL:
        try:
            sc = script_master_service.get_scrip_code(sym, "N")
            if not sc:
                continue
            snap = market_service.get_market_snapshot(sc, "N", "C")
            data_arr = (snap.get("body") or snap).get("Data", [])
            if not data_arr:
                continue
            results.append(_snapshot_to_dict(sym, sc, data_arr[0], "NSE", "N", "C"))
        except Exception:
            continue

    if not results:
        return jsonify({"trending": [], "count": 0}), 200

    # Sort by volume descending; tie-break by absolute % change
    results.sort(key=lambda s: (s["volume"], abs(s["changePercent"])), reverse=True)
    return jsonify({"trending": results[:limit], "count": min(limit, len(results))}), 200


# ─── /sentiment ───────────────────────────────────────────────────────────────

@stocks_bp.route("/sentiment", methods=["POST"])
def analyse_sentiment():
    """
    POST /api/stocks/sentiment
    Body: { "stock_name": "Reliance Industries", "ticker": "RELIANCE.NS" }

    Fetches Google News RSS, filters financial articles, runs FinBERT sentiment
    analysis and returns a summary.
    """
    body = request.get_json(silent=True) or {}
    stock_name = str(body.get("stock_name", "")).strip()
    ticker     = str(body.get("ticker", "")).strip()

    if not stock_name and not ticker:
        return jsonify({"error": "Provide stock_name or ticker"}), 400

    try:
        from services.sentiment_service import run_sentiment_pipeline
        result = run_sentiment_pipeline(stock_name, ticker)
        return jsonify(result), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── /watchlist ───────────────────────────────────────────────────────────────

@stocks_bp.route("/watchlist", methods=["GET"])
@jwt_required()
def get_watchlist():
    """GET /api/stocks/watchlist
    Returns authenticated user's watchlist entries.
    """
    user_id = int(get_jwt_identity())
    items = Watchlist.query.filter_by(user_id=user_id).order_by(Watchlist.created_at.desc()).all()
    return jsonify({"watchlist": [item.to_dict() for item in items], "count": len(items)}), 200


@stocks_bp.route("/watchlist", methods=["POST"])
@jwt_required()
def add_watchlist_item():
    """POST /api/stocks/watchlist
    Body: { "symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE" }
    """
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    symbol = str(body.get("symbol", "")).strip().upper()
    name = str(body.get("name", "")).strip() or None
    exchange = str(body.get("exchange", "NSE")).strip().upper() or "NSE"

    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    existing = Watchlist.query.filter_by(user_id=user_id, symbol=symbol).first()
    if existing:
        return jsonify({"message": "Symbol already in watchlist", "item": existing.to_dict()}), 200

    item = Watchlist(user_id=user_id, symbol=symbol, name=name, exchange=exchange)
    try:
        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Added to watchlist", "item": item.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add watchlist item", "message": str(e)}), 500


@stocks_bp.route("/watchlist/<symbol>", methods=["DELETE"])
@jwt_required()
def remove_watchlist_item(symbol):
    """DELETE /api/stocks/watchlist/<symbol>"""
    user_id = int(get_jwt_identity())
    target_symbol = symbol.strip().upper()

    item = Watchlist.query.filter_by(user_id=user_id, symbol=target_symbol).first()
    if not item:
        return jsonify({"error": "Symbol not found in watchlist"}), 404

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Removed from watchlist", "symbol": target_symbol}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to remove watchlist item", "message": str(e)}), 500
