"""
Simple rebuild webhook - triggers docker compose rebuild when called with correct token.
Runs as a container in the same compose stack.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import json

TOKEN = os.environ.get('REBUILD_TOKEN', 'changeme')

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/rebuild' and self.headers.get('X-Token') == TOKEN:
            # Run rebuild in background
            subprocess.Popen([
                'docker', 'compose',
                '-f', 'docker-compose.existing-infra.yml',
                'up', '-d', '--build'
            ])
            self.send_response(202)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'rebuilding'}).encode())
        else:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'forbidden'}).encode())

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[webhook] {args[0]}")

if __name__ == '__main__':
    print(f"[webhook] Starting on port 9999")
    HTTPServer(('0.0.0.0', 9999), Handler).serve_forever()
