"""
mcp_style_server.py
Week 5 — Building Servers

Run with:  python3 mcp_style_server.py
Then in another terminal:  curl -X POST http://localhost:8765/tools/lookup_order \\
                                  -H "Content-Type: application/json" \\
                                  -d '{"order_id": "ORD-9911"}'

WHY THIS IS A .py FILE, NOT A NOTEBOOK:
A real server calls something like `uvicorn.run(app)` or `HTTPServer.serve_forever()` —
it blocks, listening for requests, until you kill it. Running that in a notebook cell
would hang the kernel indefinitely. Servers are one of the clearest cases in this whole
programme where "the concept can't be explained with ipynb."

WHAT THIS ACTUALLY DEMONSTRATES:
This uses only Python's built-in `http.server` (no FastAPI/uvicorn/mcp-sdk installs
required) to show the *request/response lifecycle* that FastMCP, FastAPI, and the real
MCP Python SDK all build on top of: receive a request -> parse it -> dispatch to a
registered tool function -> return a structured JSON response. The production version in
Week 5's full curriculum swaps this for FastMCP's `@mcp.tool()` decorator pattern (see
Week 4's `03_tool_and_config_patterns.ipynb` for that decorator pattern in isolation) and
gains transport options (stdio/HTTP), schema generation, and the MCP Inspector for free —
but the underlying lifecycle shown here doesn't change.
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("mcp_style_server")

# --- Tool registry, same decorator pattern taught in Week 4 -----------------

TOOL_REGISTRY = {}


def tool(func):
    TOOL_REGISTRY[func.__name__] = func
    return func


@tool
def lookup_order(order_id: str) -> dict:
    return {"order_id": order_id, "status": "shipped", "eta_days": 2}


@tool
def check_refund_policy(product_category: str) -> dict:
    return {"product_category": product_category, "refund_window_days": 30}


# --- Minimal HTTP request handler ------------------------------------------

class ToolRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        # Expected path shape: /tools/<tool_name>
        parts = self.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "tools":
            self._send_json(404, {"error": "not found"})
            return

        tool_name = parts[1]
        if tool_name not in TOOL_REGISTRY:
            logger.warning("unknown tool requested: %s", tool_name)
            self._send_json(404, {"error": f"unknown tool '{tool_name}'"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(body_raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        logger.info("dispatching tool=%s payload=%s", tool_name, payload)
        try:
            result = TOOL_REGISTRY[tool_name](**payload)
        except TypeError as e:
            self._send_json(400, {"error": f"bad arguments for '{tool_name}': {e}"})
            return

        self._send_json(200, {"tool": tool_name, "result": result})

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Route the default access log through our structured logger instead of stderr.
        logger.info("%s - %s", self.address_string(), format % args)


def main():
    port = 8765
    server = HTTPServer(("localhost", port), ToolRequestHandler)
    logger.info("MCP-style tool server listening on http://localhost:%s", port)
    logger.info("Registered tools: %s", list(TOOL_REGISTRY.keys()))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
