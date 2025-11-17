import http.server
import socketserver

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

with socketserver.TTCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()
