"""
Code Review Assistant - Flask Backend
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from analysis import analyze_code

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS - restrict to local frontend in production
CORS(app, origins=os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500,null").split(","))

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour", "20 per minute"],
    storage_uri="memory://",
)

SUPPORTED_LANGUAGES = {"python", "java", "javascript", "typescript", "cpp", "c", "go", "rust"}

MAX_CODE_LENGTH = int(os.getenv("MAX_CODE_LENGTH", 50_000))  # chars


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.0.0"})


@app.route("/languages", methods=["GET"])
def languages():
    return jsonify({"supported": list(SUPPORTED_LANGUAGES)})


@app.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def analyze():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    code = data.get("code", "").strip()
    language = data.get("language", "python").strip().lower()
    prompt = data.get("prompt", "").strip()

    # Validation
    if not code:
        return jsonify({"error": "Code field is required"}), 400

    if len(code) > MAX_CODE_LENGTH:
        return jsonify({"error": f"Code exceeds maximum length of {MAX_CODE_LENGTH} characters"}), 400

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": f"Unsupported language. Supported: {', '.join(SUPPORTED_LANGUAGES)}"}), 400

    if len(prompt) > 1000:
        return jsonify({"error": "Custom prompt too long (max 1000 characters)"}), 400

    try:
        result = analyze_code(code, language=language, prompt=prompt or None)
        logger.info("Analysis completed for language=%s, code_len=%d", language, len(code))
        return jsonify(result)
    except Exception as e:
        logger.exception("Unexpected error during analysis")
        return jsonify({"error": "Internal server error. Check server logs."}), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": f"Rate limit exceeded: {e.description}"}), 429


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", 5000))

    if debug_mode:
        logger.warning("Running in DEBUG mode — do NOT use in production!")

    app.run(host="127.0.0.1", port=port, debug=debug_mode)
