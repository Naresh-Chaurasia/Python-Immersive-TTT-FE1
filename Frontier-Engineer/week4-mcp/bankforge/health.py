"""
BankForge — health check endpoint.

Runs a tiny stdlib-only HTTP server on its own port in a background thread,
separate from whatever transport the MCP server itself uses (stdio or
streamable-http). This keeps health checks dependency-free and independent
of the MCP SDK's own transport plumbing -- Docker Compose's healthcheck
directive hits this port directly.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from logging_config import get_logger, trace

logger = get_logger(__name__)

_START_TIME = time.time()


def _make_handler(service_name: str):
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/health":
                self.send_response(404)
                self.end_headers()
                return
            payload = {
                "status": "ok",
                "service": service_name,
                "uptime_seconds": round(time.time() - _START_TIME, 1),
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            # Route the base class's own access-log lines through our
            # structured logger instead of stderr, so all output stays
            # consistent JSON.
            logger.debug(f"health check request: {format % args}")

    return HealthHandler


@trace(logger)
def start_health_server(service_name: str, port: int = 8080) -> ThreadingHTTPServer:
    """Starts the health server in a daemon thread and returns the server
    object (call `.shutdown()` on it for a clean stop, e.g. in tests)."""
    handler_cls = _make_handler(service_name)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check endpoint listening on :{port}/health for service '{service_name}'")
    return server


if __name__ == "__main__":
    import urllib.request

    server = start_health_server("selftest-service", port=8099)
    time.sleep(0.2)  # give the thread a moment to bind
    with urllib.request.urlopen("http://localhost:8099/health") as resp:
        print(resp.status, resp.read().decode())
    server.shutdown()
