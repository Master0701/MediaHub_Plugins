from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class _RequestHandler(BaseHTTPRequestHandler):
    routes: dict[str, Callable] = {}
    post_routes: dict[str, Callable] = {}

    def _write(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = self.routes.get(self.path.split("?", 1)[0])
        if not route:
            return self._write(404, "application/json; charset=utf-8", b'{"error":"not_found"}')
        try:
            self._write(*route())
        except Exception as error:
            self._write(500, "application/json; charset=utf-8", json.dumps({"ok": False, "error": str(error)}).encode("utf-8"))

    def do_POST(self):
        route = self.post_routes.get(self.path.split("?", 1)[0])
        if not route:
            return self._write(404, "application/json; charset=utf-8", b'{"error":"not_found"}')
        try:
            length = min(int(self.headers.get("Content-Length", "0") or 0), 1048576)
            payload = json.loads((self.rfile.read(length) if length else b"{}").decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON-Objekt erwartet")
            self._write(*route(payload))
        except Exception as error:
            self._write(400, "application/json; charset=utf-8", json.dumps({"ok": False, "error": str(error)}).encode("utf-8"))

    def log_message(self, format, *args):
        return


class LocalWebServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = int(port)
        self._server = None
        self._thread = None

    def add_route(self, path, callback):
        _RequestHandler.routes[path] = callback

    def add_post_route(self, path, callback):
        _RequestHandler.post_routes[path] = callback

    def start(self):
        if self._server is not None:
            return
        self._server = ThreadingHTTPServer((self.host, self.port), _RequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="MediaHubWebRuntime", daemon=True)
        self._thread.start()

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    @property
    def running(self):
        return self._server is not None
