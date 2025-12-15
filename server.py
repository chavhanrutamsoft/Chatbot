#!/usr/bin/env python3
"""
Simple HTTP server for the QuotePlan RAG Chatbot
Serves the web interface and handles API requests
"""

from asyncio import subprocess
import http.server
import socketserver
import json
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Import the query bot as a module so we can call it directly
import query_bot

PORT = 8000
CHATBOT_DIR = Path(__file__).parent


class ChatbotHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for the chatbot"""

    def do_GET(self):
        """Serve static files (HTML, CSS, JS)"""
        if self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
        
        # Set proper content type for different files
        if self.path.endswith('.css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.end_headers()
            file_path = CHATBOT_DIR / self.path.lstrip('/')
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        elif self.path.endswith('.js'):
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.end_headers()
            file_path = CHATBOT_DIR / self.path.lstrip('/')
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            super().do_GET()

    def do_POST(self):
        """Handle API requests"""
        if self.path == '/api':
            # Get the content length
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body)
                question = data.get('question', '').strip()

                if not question:
                    self.send_json_response({'error': 'Question is required'}, 400)
                    return

                # Call the Python query bot directly (in a thread with timeout)
                # This avoids subprocess parsing and gives structured JSON.
                executor = ThreadPoolExecutor(max_workers=2)
                future = executor.submit(query_bot.answer_structured, question, int(data.get('top_k', 5)), False)
                try:
                    out = future.result(timeout=60)
                    # Normalize error keys so frontend shows a clear message
                    if isinstance(out, dict):
                        # If the backend indicated failure but didn't provide an 'error' key,
                        # copy any human message from 'answer' into 'error' so UI can display it.
                        if not out.get('success', True) and 'error' not in out:
                            out = dict(out)
                            out['error'] = out.get('answer') or 'Unknown error'
                        # Remove retrieved/context sources from the response sent to the UI
                        if 'retrieved' in out:
                            out = dict(out)
                            out.pop('retrieved', None)
                    # Ensure it's JSON-serializable
                    self.send_json_response(out)
                except FuturesTimeout:
                    future.cancel()
                    self.send_json_response({'success': False, 'error': 'Query timed out. Please try again.'}, 500)
                except Exception as e:
                    self.send_json_response({'success': False, 'error': f'Server error: {e}'}, 500)

            except subprocess.TimeoutExpired:
                self.send_json_response(
                    {'error': 'Query timed out. Please try again.'},
                    500
                )
            except json.JSONDecodeError:
                self.send_json_response(
                    {'error': 'Invalid JSON in request'},
                    400
                )
            except Exception as e:
                print(f"Error: {e}")
                self.send_json_response(
                    {'error': f'Server error: {str(e)}'},
                    500
                )
        else:
            self.send_json_response({'error': 'Not found'}, 404)

    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    @staticmethod
    def extract_answer(output):
        """Extract the answer from the Python script output"""
        lines = output.split('\n')
        answer_started = False
        answer_lines = []

        for line in lines:
            if '✅ Answer:' in line:
                answer_started = True
                continue

            if answer_started and line.strip():
                answer_lines.append(line.strip())

        if answer_lines:
            return '\n'.join(answer_lines)
        return None

    def end_headers(self):
        """Override to add CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        """Customize logging"""
        print(f"[{self.client_address[0]}] {format % args}")


if __name__ == '__main__':
    handler = ChatbotHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"🚀 QuotePlan Chatbot Server running at http://localhost:{PORT}")
        print(f"📝 Open your browser and navigate to http://localhost:{PORT}")
        print(f"Press Ctrl+C to stop the server\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✋ Server stopped.")
