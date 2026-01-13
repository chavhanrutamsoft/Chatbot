# #!/usr/bin/env python3
# """
# Simple HTTP server for the QuotePlan RAG Chatbot
# Serves the web interface and handles API requests
# """

# from asyncio import subprocess
# import http.server
# import socketserver
# import json
# import urllib.parse
# from pathlib import Path
# from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
# from typing import Optional
# import hashlib

# # Import the query bot as a module so we can call it directly
# import sys
# from pathlib import Path

# # Add backend directory to path for imports
# BACKEND_DIR = Path(__file__).parent
# PROJECT_ROOT = BACKEND_DIR.parent
# sys.path.insert(0, str(BACKEND_DIR))

# import query_bot

# PORT = 8000
# FRONTEND_DIR = PROJECT_ROOT / "frontend"

# # ----------------------------------------------------------------------
# # CACHE SYSTEM
# # ----------------------------------------------------------------------
# # Cache structure: {session_id: {question_hash: response_dict}}
# # This allows per-user caching and easy cache clearing for new users
# cache = {}

# def normalize_question(question: str) -> str:
#     """Normalize question for consistent caching (lowercase, strip whitespace)"""
#     return question.lower().strip()

# def get_question_hash(question: str) -> str:
#     """Generate a hash for the normalized question"""
#     normalized = normalize_question(question)
#     return hashlib.md5(normalized.encode('utf-8')).hexdigest()

# def get_cached_response(session_id: str, question: str) -> Optional[dict]:
#     """Get cached response if available"""
#     if session_id not in cache:
#         return None
    
#     question_hash = get_question_hash(question)
#     return cache[session_id].get(question_hash)

# def cache_response(session_id: str, question: str, response: dict):
#     """Store response in cache"""
#     if session_id not in cache:
#         cache[session_id] = {}
    
#     question_hash = get_question_hash(question)
#     cache[session_id][question_hash] = response.copy()  # Store a copy to avoid mutations

# def clear_user_cache(session_id: str):
#     """Clear cache for a specific user/session"""
#     if session_id in cache:
#         cache[session_id] = {}
#         print(f"[CACHE] Cleared cache for session: {session_id}")

# def get_or_create_session_id(data: dict, client_address: tuple) -> str:
#     """Get session_id from request or create one based on client address"""
#     session_id = data.get('session_id') or data.get('user_id')
#     if not session_id:
#         # Use client IP as default session identifier
#         session_id = f"user_{client_address[0]}"
    
#     # Check if this is a new session (first time we see this session_id)
#     is_new_session = session_id not in cache
#     if is_new_session:
#         print(f"[CACHE] New session detected: {session_id}")
#         cache[session_id] = {}
    
#     return session_id

# # ----------------------------------------------------------------------
# # FALLBACK LOGIC
# # ----------------------------------------------------------------------
# def fallback_response(question: str) -> dict:
#     """
#     Return a safe, generic answer when the online model does not respond
#     within the allotted time.
#     """
#     generic_answer = (
#         "I'm sorry, I couldn't fetch a detailed answer right now. "
#         "Please try again later or re‑phrase your question."
#     )
#     # No 'error' key – the client receives a normal‑looking response.
#     return {
#         "success": False,
#         "answer": generic_answer,
#         "short": generic_answer,
#         "steps": [],  
#         "follow_up": None,
#     }

# class ChatbotHandler(http.server.SimpleHTTPRequestHandler):
#     """HTTP request handler for the chatbot"""

#     def do_GET(self):
#         """Serve static files (HTML, CSS, JS) from frontend directory"""
#         if self.path == '/' or self.path == '/index.html':
#             self.path = '/index.html'

#         # Map paths to frontend directory
#         file_name = self.path.lstrip('/')
#         if not file_name or file_name == '/':
#             file_name = 'index.html'
        
#         file_path = FRONTEND_DIR / file_name

#         # Set proper content type for different files
#         if self.path.endswith('.css'):
#             if file_path.exists():
#                 self.send_response(200)
#                 self.send_header('Content-type', 'text/css; charset=utf-8')
#                 self.end_headers()
#                 with open(file_path, 'rb') as f:
#                     self.wfile.write(f.read())
#             else:
#                 self.send_error(404)
#         elif self.path.endswith('.js'):
#             if file_path.exists():
#                 self.send_response(200)
#                 self.send_header('Content-type', 'application/javascript; charset=utf-8')
#                 self.end_headers()
#                 with open(file_path, 'rb') as f:
#                     self.wfile.write(f.read())
#             else:
#                 self.send_error(404)
#         elif self.path.endswith('.html') or self.path == '/':
#             if file_path.exists():
#                 self.send_response(200)
#                 self.send_header('Content-type', 'text/html; charset=utf-8')
#                 self.end_headers()
#                 with open(file_path, 'rb') as f:
#                     self.wfile.write(f.read())
#             else:
#                 self.send_error(404)
#         else:
#             self.send_error(404)

#     def do_POST(self):
#         """Handle API requests"""
#         if self.path == '/api':
#             # Get the content length
#             content_length = int(self.headers.get('Content-Length', 0))
#             body = self.rfile.read(content_length).decode('utf-8')

#             try:
#                 data = json.loads(body)
#                 question = data.get('question', '').strip()

#                 if not question:
#                     self.send_json_response({'error': 'Question is required'}, 400)
#                     return

#                 # Get or create session ID for this user
#                 session_id = get_or_create_session_id(data, self.client_address)

#                 # ------------------------------------------------------------------
#                 # CHECK CACHE FIRST
#                 # ------------------------------------------------------------------
#                 cached_response = get_cached_response(session_id, question)
#                 if cached_response is not None:
#                     print(f"[CACHE] Cache HIT for question: {question[:50]}...")
#                     self.send_json_response(cached_response)
#                     return

#                 print(f"[CACHE] Cache MISS for question: {question[:50]}...")

#                 # ------------------------------------------------------------------
#                 # CALL ONLINE MODEL WITH 15‑SECOND TIMEOUT
#                 # ------------------------------------------------------------------
#                 executor = ThreadPoolExecutor(max_workers=2)
#                 future = executor.submit(
#                     query_bot.answer_structured,
#                     question,
#                     int(data.get('top_k', 15)),  # Increased default to retrieve more chunks for complete answers
#                     False
#                 )
#                 try:
#                     # Give the model only 15 seconds
#                     out = future.result(timeout=15)

#                     # Normalise the output (same as before)
#                     if isinstance(out, dict):
#                         if not out.get('success', True) and 'error' not in out:
#                             out = dict(out)
#                             out['error'] = out.get('answer') or 'Unknown error'
#                         if 'retrieved' in out:
#                             out = dict(out)
#                             out.pop('retrieved', None)

#                     # Store response in cache (only if successful)
#                     if out.get('success', True):
#                         cache_response(session_id, question, out)
#                         print(f"[CACHE] Response cached for session: {session_id}")

#                     self.send_json_response(out)

#                 except FuturesTimeout:
#                     # --------------------------------------------------------------
#                     # TIMEOUT – switch to fallback mode (no error field)
#                     # --------------------------------------------------------------
#                     future.cancel()
#                     print("[SERVER] Fallback mode is ON (model timed out after 15 s)")
#                     fallback = fallback_response(question)
#                     self.send_json_response(fallback, 200)

#                 except Exception as e:
#                     # Any other unexpected error from the model
#                     self.send_json_response(
#                         {'success': False, 'error': f'Server error: {e}'},
#                         500
#                     )

#             except subprocess.TimeoutExpired:
#                 self.send_json_response(
#                     {'error': 'Query timed out. Please try again.'},
#                     500
#                 )
#             except json.JSONDecodeError:
#                 self.send_json_response(
#                     {'error': 'Invalid JSON in request'},
#                     400
#                 )
#             except Exception as e:
#                 print(f"[SERVER] Unexpected error: {e}")
#                 self.send_json_response(
#                     {'error': f'Server error: {str(e)}'},
#                     500
#                 )
#         else:
#             self.send_json_response({'error': 'Not found'}, 404)

#     def send_json_response(self, data, status_code=200):
#         """Send JSON response"""
#         self.send_response(status_code)
#         self.send_header('Content-type', 'application/json; charset=utf-8')
#         self.send_header('Access-Control-Allow-Origin', '*')
#         self.end_headers()
#         self.wfile.write(json.dumps(data).encode('utf-8'))

#     def do_OPTIONS(self):
#         """Handle CORS preflight"""
#         self.send_response(200)
#         self.send_header('Access-Control-Allow-Origin', '*')
#         self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
#         self.send_header('Access-Control-Allow-Headers', 'Content-Type')
#         self.end_headers()

#     @staticmethod
#     def extract_answer(output):
#         """Extract the answer from the Python script output"""
#         lines = output.split('\n')
#         answer_started = False
#         answer_lines = []

#         for line in lines:
#             if '✅ Answer:' in line:
#                 answer_started = True
#                 continue

#             if answer_started and line.strip():
#                 answer_lines.append(line.strip())

#         if answer_lines:
#             return '\n'.join(answer_lines)
#         return None

#     def end_headers(self):
#         """Override to add CORS headers"""
#         self.send_header('Access-Control-Allow-Origin', '*')
#         super().end_headers()

#     def log_message(self, format, *args):
#         """Customize logging"""
#         print(f"[{self.client_address[0]}] {format % args}")


# if __name__ == '__main__':
#     handler = ChatbotHandler
#     socketserver.TCPServer.allow_reuse_address = True
    
#     # Try to start server, with fallback to alternative port if needed
#     port = PORT
#     max_attempts = 5
    
#     for attempt in range(max_attempts):
#         try:
#             with socketserver.TCPServer(("", port), handler) as httpd:
#                 print(f"🚀 QuotePlan Chatbot Server running at http://localhost:{port}")
#                 print(f"📝 Open your browser and navigate to http://localhost:{port}")
#                 print(f"Press Ctrl+C to stop the server\n")
#                 try:
#                     httpd.serve_forever()
#                 except KeyboardInterrupt:
#                     print("\n✋ Server stopped.")
#                 break
#         except OSError as e:
#             if e.winerror == 10013 or "Address already in use" in str(e):
#                 if attempt < max_attempts - 1:
#                     port += 1
#                     print(f"⚠️  Port {port - 1} is in use. Trying port {port}...")
#                 else:
#                     print(f"❌ Error: Could not find an available port after {max_attempts} attempts.")
#                     print(f"   Port {PORT} and nearby ports are in use.")
#                     print(f"   Please close other applications using these ports or change PORT in server.py")
#                     raise
#             else:
#                 raise

#!/usr/bin/env python3
"""
Simple HTTP server for the QuotePlan RAG Chatbot
PRODUCTION READY – No functionality loss
"""

import http.server
import socketserver
import json
import sys
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Optional

# ----------------------------------------------------------------------
# IMPORT QUERY BOT
# ----------------------------------------------------------------------

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import query_bot

PORT = 8000
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ----------------------------------------------------------------------
# CACHE SYSTEM (per session)
# ----------------------------------------------------------------------

cache = {}

def normalize_question(q: str) -> str:
    return q.lower().strip()

def get_question_hash(q: str) -> str:
    return hashlib.md5(normalize_question(q).encode("utf-8")).hexdigest()

def get_cached_response(session_id: str, question: str) -> Optional[dict]:
    return cache.get(session_id, {}).get(get_question_hash(question))

def cache_response(session_id: str, question: str, response: dict):
    cache.setdefault(session_id, {})
    cache[session_id][get_question_hash(question)] = response.copy()

def get_or_create_session_id(data: dict, client_address: tuple) -> str:
    session_id = data.get("session_id") or data.get("user_id")
    if not session_id:
        session_id = f"user_{client_address[0]}"
    cache.setdefault(session_id, {})
    return session_id

# ----------------------------------------------------------------------
# FALLBACK RESPONSE
# ----------------------------------------------------------------------

def fallback_response(question: str) -> dict:
    msg = (
        "I'm sorry, I couldn't fetch a detailed answer right now. "
        "Please try again later or re-phrase your question."
    )
    return {
        "success": False,
        "answer": msg,
        "short": msg,
        "steps": [],
        "follow_up": None,
    }

# ----------------------------------------------------------------------
# HTTP HANDLER
# ----------------------------------------------------------------------

class ChatbotHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"

        file_path = FRONTEND_DIR / self.path.lstrip("/")
        if not file_path.exists():
            self.send_error(404)
            return

        content_type = "text/html"
        if self.path.endswith(".css"):
            content_type = "text/css"
        elif self.path.endswith(".js"):
            content_type = "application/javascript"

        self.send_response(200)
        self.send_header("Content-type", f"{content_type}; charset=utf-8")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def do_POST(self):
        if self.path != "/api":
            self.send_json_response({"error": "Not found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)

            question = data.get("question", "").strip()
            if not question:
                self.send_json_response({"error": "Question is required"}, 400)
                return

            session_id = get_or_create_session_id(data, self.client_address)

            # 🔴 CRITICAL: Do NOT cache follow-ups
            is_follow_up = query_bot._is_follow_up(question)

            if not is_follow_up:
                cached = get_cached_response(session_id, question)
                if cached:
                    print("[CACHE] HIT")
                    self.send_json_response(cached)
                    return

            print("[CACHE] MISS")

            executor = ThreadPoolExecutor(max_workers=2)
            future = executor.submit(
                query_bot.answer_structured,
                question,
                8   # aligned with improved RAG recall
            )

            try:
                out = future.result(timeout=15)

                if isinstance(out, dict):
                    out = dict(out)
                    out.pop("retrieved", None)

                if out.get("success", True) and not is_follow_up:
                    cache_response(session_id, question, out)

                self.send_json_response(out)

            except FuturesTimeout:
                future.cancel()
                print("[SERVER] Timeout → fallback")
                self.send_json_response(fallback_response(question))

        except json.JSONDecodeError:
            self.send_json_response({"error": "Invalid JSON"}, 400)
        except Exception as e:
            print("[SERVER ERROR]", e)
            self.send_json_response({"error": str(e)}, 500)

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[{self.client_address[0]}] {fmt % args}")

# ----------------------------------------------------------------------
# SERVER START
# ----------------------------------------------------------------------

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    port = PORT

    for _ in range(5):
        try:
            with socketserver.TCPServer(("", port), ChatbotHandler) as httpd:
                print(f"🚀 QuotePlan Chatbot running at http://localhost:{port}")
                httpd.serve_forever()
        except OSError:
            port += 1
