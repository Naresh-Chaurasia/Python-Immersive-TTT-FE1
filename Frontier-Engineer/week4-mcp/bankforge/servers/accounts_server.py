"""
BankForge — accounts_server.

Exposes NeoBank India's core banking data (account records + transaction
history) as MCP tools. Every tool call is traced (ENTER/EXIT, DEBUG level)
and every account-record response passes through
guardrails.minimize_account_fields() before it leaves this server.

Run standalone for local development:
    python3 servers/accounts_server.py --transport stdio

Run for the Docker Compose multi-server demo:
    python3 servers/accounts_server.py --transport streamable-http --port 8001
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # make project root importable

import database
import guardrails
from health import start_health_server
from logging_config import get_logger, trace

from mcp.server.fastmcp import FastMCP  # requires: pip install mcp

logger = get_logger("accounts_server")

mcp = FastMCP("neobank-accounts-server")


@mcp.tool()
@trace(logger, redact=guardrails.redact_for_logging)
def get_account_summary(account_id: str, caller_scope: str) -> dict:
    """Look up a NeoBank India account's summary (type, balance, status) by
    account_id. `caller_scope` must be one of: teller, loan_officer,
    compliance_officer, admin -- controls which fields are returned
    (data minimization; compliance_officer sees KYC/risk fields, others don't).
    """
    account = database.get_account(account_id)
    if not account:
        return {"error": f"No account found for account_id '{account_id}'"}

    if caller_scope == "compliance_officer":
        customer = database.get_customer(account["customer_id"]) or {}
        account = {**account, "kyc_status": customer.get("kyc_status"), "risk_rating": customer.get("risk_rating")}

    return guardrails.minimize_account_fields(account, caller_scope)


@mcp.tool()
@trace(logger, redact=guardrails.redact_for_logging)
def get_accounts_for_customer(customer_id: str, caller_scope: str) -> list[dict]:
    """List every account belonging to a customer_id, minimized per caller_scope
    the same way get_account_summary is."""
    accounts = database.get_accounts_for_customer(customer_id)
    return [guardrails.minimize_account_fields(a, caller_scope) for a in accounts]


@mcp.tool()
@trace(logger, redact=guardrails.redact_for_logging)
def get_transaction_history(account_id: str, limit: int = 10) -> list[dict]:
    """Return up to `limit` most recent transactions for an account_id,
    most recent first. Transaction records don't carry customer PII beyond
    the account_id itself, so no additional minimization is applied here --
    scope-based restriction happens one level up, at the account-summary step.
    """
    if limit > 100:
        limit = 100  # simple guardrail against an unbounded query
    return database.get_transactions(account_id, limit=limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default=os.environ.get("MCP_TRANSPORT", "stdio"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", 8001)))
    parser.add_argument("--health-port", type=int, default=int(os.environ.get("HEALTH_PORT", 8011)))
    args = parser.parse_args()

    database.init_db(force=False)
    start_health_server("accounts_server", port=args.health_port)

    logger.info(f"Starting accounts_server via {args.transport} transport")
    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
    else:
        mcp.run(transport="stdio")
