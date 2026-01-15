#!/usr/bin/env python3
"""
Production-ready Flask application for QuotePlan RAG Chatbot
Deployment-ready with logging, error handling, caching, and health checks
"""

import os
import json
import time
import hashlib
from pathlib import Path
from collections import OrderedDict
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Import query bot
import sys
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import query_bot
from logger_config import logger

app = Flask(__name__, static_folder=str(PROJECT_ROOT / 'frontend'), static_url_path='')
CORS(app)

# Configuration
PORT = int(os.environ.get('PORT', 8000))
MAX_QUESTION_LENGTH = 1000
CACHE_MAX_SIZE = 1000
CACHE_TTL = 3600  # 1 hour
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", 30))
MAX_TOP_K = int(os.environ.get("MAX_TOP_K", 60))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", 20))

# Cache system
cache = {}

def normalize_question(q: str) -> str:
    """Normalize question for consistent caching."""
    return q.lower().strip()

def get_question_hash(q: str) -> str:
    """Generate hash for normalized question."""
    return hashlib.md5(normalize_question(q).encode("utf-8")).hexdigest()

def get_cached_response(session_id: str, question: str):
    """Get cached response if available and not expired."""
    if session_id not in cache:
        return None
    question_hash = get_question_hash(question)
    session_cache = cache[session_id]
    if question_hash not in session_cache:
        return None
    response, timestamp = session_cache[question_hash]
    if time.time() - timestamp > CACHE_TTL:
        del session_cache[question_hash]
        return None
    return response.copy()

def cache_response(session_id: str, question: str, response: dict):
    """Store response in cache with TTL and size limits."""
    if session_id not in cache:
        cache[session_id] = OrderedDict()
    question_hash = get_question_hash(question)
    session_cache = cache[session_id]
    while len(session_cache) >= CACHE_MAX_SIZE:
        session_cache.popitem(last=False)
    session_cache[question_hash] = (response.copy(), time.time())
    session_cache.move_to_end(question_hash)

def validate_question(question: str):
    """Validate question input. Returns (is_valid, error_message)."""
    if not question or not question.strip():
        return False, "Question cannot be empty"
    if len(question) > MAX_QUESTION_LENGTH:
        return False, f"Question too long (max {MAX_QUESTION_LENGTH} characters)"
    return True, None

def fallback_response(question: str) -> dict:
    """Return a safe, generic answer when the online model does not respond."""
    generic_answer = (
        "I'm sorry, I couldn't fetch a detailed answer right now. "
        "Please try again later or re-phrase your question."
    )
    return {
        "success": False,
        "answer": generic_answer,
    }

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory(PROJECT_ROOT / 'frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS)."""
    return send_from_directory(PROJECT_ROOT / 'frontend', path)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "service": "quoteplan-chatbot",
        "timestamp": time.time()
    }), 200

@app.route('/api', methods=['POST', 'OPTIONS'])
def api():
    """Handle API requests with caching and validation."""
    if request.method == 'OPTIONS':
        return '', 200
    
    start_time = time.time()
    
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        question = data.get('question', '').strip()
        
        # Validate question
        is_valid, error_msg = validate_question(question)
        if not is_valid:
            logger.warning(f"Invalid question: {error_msg}")
            return jsonify({'error': error_msg}), 400

        # Get session ID
        session_id = data.get('session_id') or data.get('user_id') or f"user_{request.remote_addr}"

        # Validate top_k input
        try:
            top_k = int(data.get('top_k', DEFAULT_TOP_K))
        except (TypeError, ValueError):
            top_k = DEFAULT_TOP_K
        top_k = max(1, min(top_k, MAX_TOP_K))
        
        # Check if follow-up (don't cache)
        is_follow_up = query_bot._is_follow_up(question)
        
        # Check cache
        if not is_follow_up:
            cached = get_cached_response(session_id, question)
            if cached:
                logger.info(f"Cache HIT for session {session_id[:8]}...")
                return jsonify(cached)
        
        logger.info(f"Cache MISS for session {session_id[:8]}..., question: {question[:50]}...")

        # Call query bot with timeout
        executor = ThreadPoolExecutor(max_workers=2)
        future = executor.submit(
            query_bot.answer_structured,
            question,
            top_k  # Production level - maximum retrieval
        )
        
        try:
            out = future.result(timeout=REQUEST_TIMEOUT_SECONDS)

            # Normalize output
            if isinstance(out, dict):
                out = dict(out)
                out.pop('retrieved', None)

            # Cache successful responses
            if out.get('success', True) and not is_follow_up:
                cache_response(session_id, question, out)

            response_time = time.time() - start_time
            logger.info(f"Request processed in {response_time:.2f}s")
            return jsonify(out)

        except FuturesTimeout:
            future.cancel()
            logger.warning(f"Request timeout for question: {question[:50]}...")
            return jsonify(fallback_response(question)), 200

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'An internal error occurred. Please try again later.'
            }), 500
        finally:
            executor.shutdown(wait=False)

    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from {request.remote_addr}")
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({
            'error': 'An internal error occurred. Please try again later.'
        }), 500

if __name__ == '__main__':
    logger.info(f"Starting QuotePlan Chatbot Flask server on port {PORT}")
    logger.info(f"Cache TTL: {CACHE_TTL}s, Max cache size: {CACHE_MAX_SIZE}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
