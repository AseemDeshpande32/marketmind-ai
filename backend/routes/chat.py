"""
Chat Route Blueprint — POST /api/chat  |  POST /api/chat/stream

Accepts a JSON body { "message": "..." } and returns an AI-generated
response from the MarketMind chat agent (Ollama / Gemma).

/api/chat        — full response as JSON (legacy)
/api/chat/stream — Server-Sent Events, one token at a time (streaming)
"""

import json
import logging
from flask import Blueprint, Response, request, jsonify, stream_with_context

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """
    POST /api/chat

    Request body (JSON):
        {
          "message": "Compare Wipro and Infosys",
          "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]  # optional
        }

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
    history = body.get("history", [])

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(message) > 2000:
        return jsonify({"error": "Message too long (maximum 2000 characters)"}), 400

    # ── Delegate to agent ───────────────────────────────────────────────────
    try:
        from services.chat_service import process_chat
        result = process_chat(message, history)
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


@chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    POST /api/chat/stream

    Same request body as /api/chat (with optional history array).
    Returns a text/event-stream (SSE) response where each event is a JSON object:

      data: {"type": "meta",  "intent": "...", "data": {...}}
      data: {"type": "token", "text": "..."}
      data: {"type": "done"}
      data: {"type": "error", "message": "..."}
    """
    body = request.get_json(silent=True)

    if not body or not isinstance(body.get("message"), str):
        return jsonify({"error": "Request body must be JSON with a 'message' string"}), 400

    message = body["message"].strip()
    history = body.get("history", [])

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(message) > 2000:
        return jsonify({"error": "Message too long (maximum 2000 characters)"}), 400

    def generate():
        try:
            from services.chat_service import stream_process_chat
            for event in stream_process_chat(message, history):
                yield f"data: {json.dumps(event)}\n\n"
        except RuntimeError as exc:
            logger.error("[CHAT STREAM] Ollama unavailable: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except Exception as exc:
            logger.exception("[CHAT STREAM] Unexpected error")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal server error'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
