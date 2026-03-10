"""
Chat Route Blueprint — POST /api/chat

Accepts a JSON body { "message": "..." } and returns an AI-generated
response from the MarketMind chat agent (Ollama / Gemma).
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """
    POST /api/chat

    Request body (JSON):
        { "message": "Compare Wipro and Infosys" }

    Response (JSON):
        {
          "response": "<AI-generated text>",
          "intent":   "comparison" | "portfolio" | "stock_query" | "general",
          "data":     { ... }   // live market data used (may be null)
        }

    Error responses:
        400  — missing or empty message
        503  — Ollama engine unreachable
        500  — unexpected server error
    """
    body = request.get_json(silent=True)

    # ── Input validation ────────────────────────────────────────────────────
    if not body or not isinstance(body.get("message"), str):
        return jsonify({"error": "Request body must be JSON with a 'message' string"}), 400

    message = body["message"].strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(message) > 2000:
        return jsonify({"error": "Message too long (maximum 2000 characters)"}), 400

    # ── Delegate to agent ───────────────────────────────────────────────────
    try:
        from services.chat_service import process_chat
        result = process_chat(message)
        return jsonify(result), 200

    except RuntimeError as exc:
        # Raised by _call_ollama when Ollama is not reachable / timed-out
        logger.error("[CHAT ROUTE] Ollama unavailable: %s", exc)
        return jsonify({
            "error":    "AI service unavailable",
            "message":  str(exc),
            "response": (
                "I'm unable to reach the AI engine right now. "
                "Please make sure Ollama is running (ollama serve) "
                "and that the Gemma model is pulled (ollama pull gemma3), "
                "then try again."
            ),
            "intent": "error",
            "data":   None,
        }), 503

    except Exception as exc:
        logger.exception("[CHAT ROUTE] Unexpected error processing chat message")
        return jsonify({
            "error":   "Internal server error",
            "message": str(exc),
        }), 500
