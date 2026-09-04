# BankForge — NeoBank India MCP Ecosystem

Week 5 capstone: three MCP servers exposing NeoBank India's account,
loan/product, and compliance/communication systems to any MCP-compatible
AI client — with scoped access, data minimization, input sanitisation,
PII-safe structured logging, and Docker Compose deployment.

See **`ARCHITECTURE.md`** for the full design write-up (the graded
architecture document). This README is setup/usage only.

## Quick start — no MCP, no Docker (verify the logic first)

```bash
pip install -r requirements.txt   # only needed for models.py / real servers; the demo below doesn't need it
python3 database.py               # seed neobank.db
python3 run_local_demo.py         # walks through every required demo scenario
```

`run_local_demo.py` calls the tool functions directly — it proves the
business logic (scoped access, compliance rules, guardrails) works before
you involve MCP transport or Docker at all. `LOG_LEVEL=DEBUG` is the
default, so you'll see every ENTER/EXIT trace line as JSON on stdout.

## Running a server for real (requires `pip install mcp`)

```bash
python3 servers/accounts_server.py --transport stdio
```

Or wire it into Claude Desktop using `claude_desktop_config.example.json`
(copy to Claude Desktop's real config location, fix the absolute paths).

## Running the full 3-server ecosystem with Docker Compose

```bash
docker compose up --build
```

Then, as deployment evidence:

```bash
curl http://localhost:8011/health   # accounts_server
curl http://localhost:8012/health   # products_server
curl http://localhost:8013/health   # compliance_comms_server
```

Each should return `{"status": "ok", "service": "...", "uptime_seconds": ...}`.

Server logs stream to `docker compose logs -f accounts_server` (etc.) as
structured JSON, one object per line.

## Running tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

## Project layout

```
bankforge/
├── ARCHITECTURE.md              The graded architecture document
├── logging_config.py            DEBUG-default structured logging + @trace decorator
├── guardrails.py                Scoped access, data minimization, PII redaction, sanitisation
├── database.py                  Shared SQLite mock NeoBank India DB
├── models.py                    Pydantic schemas
├── health.py                    Stdlib-only /health endpoint, run per server
├── run_local_demo.py            Walks through every required demo scenario, no MCP/Docker needed
├── servers/
│   ├── accounts_server.py         Account data + transaction history
│   ├── products_server.py         Loan/product catalogue
│   └── compliance_comms_server.py KYC/compliance + customer communication
├── docker/
│   ├── Dockerfile.accounts
│   ├── Dockerfile.products
│   └── Dockerfile.compliance_comms
├── docker-compose.yml            Orchestrates all 3 + shared DB volume + health checks
├── tests/                        pytest suite for database.py, guardrails.py, logging_config.py
├── claude_desktop_config.example.json
└── requirements.txt
```

## A note on how this was built and tested

`mcp`, `pydantic`, and `pytest` were not installed in the environment used
to build this (no network access to install them), so:

- **Fully tested, by actually running the code:** `logging_config.py`,
  `guardrails.py`, `database.py`, and every tool function's underlying
  logic (via a minimal test-only stub of the `mcp` package standing in for
  the real `FastMCP` class, plus `run_local_demo.py`, both run end to end
  with real output inspected).
- **Written against the current MCP SDK API, but not executed against the
  real package:** the `@mcp.tool()` registration, `FastMCP(...)`
  construction, and `mcp.run(transport=...)` calls in each server file.
  These follow the documented FastMCP pattern, but if the installed SDK
  version has moved (MCP's Python SDK is under active development),
  double-check `mcp.run()`'s exact keyword arguments for `host`/`port`
  against whatever version `pip install mcp` gives you — the tool-function
  bodies underneath won't need to change either way.
- **Written but not executed at all:** the Dockerfiles and
  `docker-compose.yml` (no Docker daemon in this environment). Syntax and
  structure follow standard Compose v3.9 conventions; run
  `docker compose config` first to validate before `up --build` if you
  want an extra check.

Before your demo: run `python3 run_local_demo.py` first (fast, proves the
logic), then `pip install mcp` and try one server with `--transport stdio`,
then `docker compose up --build` last.
