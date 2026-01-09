#!/usr/bin/env python3
"""
Flask application for Render deployment
This wraps the existing query_bot functionality in a Flask app
"""

import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Import query bot
import sys
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import query_bot

app = Flask(__name__, static_folder=str(PROJECT_ROOT / 'frontend'), static_url_path='')
CORS(app)

# Get port from environment variable (Render sets this)
PORT = int(os.environ.get('PORT', 8000))

def fallback_response(question: str) -> dict:
    """Return a safe, generic answer when the online model does not respond"""
    generic_answer = (
        "I'm sorry, I couldn't fetch a detailed answer right now. "
        "Please try again later or re‑phrase your question."
    )
    return {
        "success": False,
        "answer": generic_answer,
        "short": generic_answer,
        "steps": [],
        "follow_up": None,
    }

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory(PROJECT_ROOT / 'frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS)"""
    return send_from_directory(PROJECT_ROOT / 'frontend', path)

@app.route('/api', methods=['POST', 'OPTIONS'])
def api():
    """Handle API requests"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        # Call query bot with timeout
        executor = ThreadPoolExecutor(max_workers=2)
        future = executor.submit(
            query_bot.answer_structured,
            question,
            int(data.get('top_k', 5)),
            False
        )
        
        try:
            # Give the model 15 seconds
            out = future.result(timeout=15)

            # Normalize the output
            if isinstance(out, dict):
                if not out.get('success', True) and 'error' not in out:
                    out = dict(out)
                    out['error'] = out.get('answer') or 'Unknown error'
                if 'retrieved' in out:
                    out = dict(out)
                    out.pop('retrieved', None)

            return jsonify(out)

        except FuturesTimeout:
            future.cancel()
            print("[SERVER] Fallback mode is ON (model timed out after 15 s)")
            fallback = fallback_response(question)
            return jsonify(fallback), 200

        except Exception as e:
            return jsonify({'success': False, 'error': f'Server error: {e}'}), 500

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in request'}), 400
    except Exception as e:
        print(f"[SERVER] Unexpected error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
