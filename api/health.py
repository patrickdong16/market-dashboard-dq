"""Health check endpoint - verifies env vars are loaded."""
from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        key = os.environ.get('EODHD_API_KEY', '')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'eodhd_key_set': bool(key),
            'eodhd_key_length': len(key),
            'eodhd_key_prefix': key[:4] + '...' if len(key) > 4 else '(empty)',
        }).encode())
