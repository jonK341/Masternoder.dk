#!/usr/bin/env python3
"""
Python reverse proxy for the Flask application.

The production python-proxy.service expects this file at
/var/www/html/vidgenerator/python_proxy_server.py and forwards traffic to the
primary uWSGI instance on 127.0.0.1:5000.
"""
import socketserver
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler


FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_URL = f"http://{FLASK_HOST}:{FLASK_PORT}"


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler that proxies requests to Flask."""

    def do_GET(self):
        self._proxy_request("GET")

    def do_POST(self):
        self._proxy_request("POST")

    def do_PUT(self):
        self._proxy_request("PUT")

    def do_DELETE(self):
        self._proxy_request("DELETE")

    def do_OPTIONS(self):
        self._proxy_request("OPTIONS")

    def do_PATCH(self):
        self._proxy_request("PATCH")

    def _proxy_request(self, method):
        try:
            path = self.path
            if path.startswith("/vidgenerator"):
                flask_path = path[len("/vidgenerator"):] or "/"
            else:
                flask_path = path
            if not flask_path.startswith("/"):
                flask_path = "/" + flask_path

            flask_url = f"{FLASK_URL}{flask_path}"
            print(f"[Proxy] {method} {path} -> {flask_url}", file=sys.stderr, flush=True)

            headers = {}
            for key, value in self.headers.items():
                if key.lower() not in {
                    "connection",
                    "keep-alive",
                    "proxy-authenticate",
                    "proxy-authorization",
                    "te",
                    "trailers",
                    "transfer-encoding",
                    "upgrade",
                }:
                    headers[key] = value

            headers["X-Forwarded-For"] = self.client_address[0]
            headers["X-Forwarded-Proto"] = "https"
            headers["X-Forwarded-Host"] = self.headers.get("Host", "")
            headers["X-Forwarded-Prefix"] = "/vidgenerator"
            headers["X-Script-Name"] = "/vidgenerator"

            body = None
            if method in {"POST", "PUT", "PATCH"}:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)

            req = urllib.request.Request(flask_url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    self._send_proxy_response(response.getcode(), dict(response.headers), response.read())
            except urllib.error.HTTPError as exc:
                self._send_proxy_response(exc.code, dict(exc.headers), exc.read())
            except Exception as exc:
                print(f"Error proxying to Flask: {exc}", file=sys.stderr, flush=True)
                self.send_error(502, f"Bad Gateway: {exc}")
        except Exception as exc:
            print(f"Error in proxy handler: {exc}", file=sys.stderr, flush=True)
            self.send_error(500, f"Internal Server Error: {exc}")

    def _send_proxy_response(self, status_code, response_headers, response_body):
        self.send_response(status_code)
        for key, value in response_headers.items():
            if key.lower() not in {"connection", "keep-alive", "transfer-encoding"}:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        print(f"[Proxy] {format % args}", file=sys.stderr, flush=True)


def run_proxy(port=8080):
    with socketserver.TCPServer(("", port), ProxyHandler) as httpd:
        print(f"Python reverse proxy running on port {port}", file=sys.stderr, flush=True)
        print(f"Proxying /vidgenerator/* to {FLASK_URL}", file=sys.stderr, flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    run_proxy(int(sys.argv[1]) if len(sys.argv) > 1 else 8080)
