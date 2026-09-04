"""
BankForge — products_server.

Exposes NeoBank India's loan/product catalogue as MCP tools. This server
deliberately does NOT reach into customer-specific compliance data (KYC,
risk rating) -- that's compliance_comms_server's job. An AI client wanting
"is this customer eligible for this loan" composes both servers itself;
keeping the boundary here is what the scoped-access / least-privilege
requirement actually means in practice: this server can't see KYC data
even if a bug tried to make it.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database
from health import start_health_server
from logging_config import get_logger, trace

from mcp.server.fastmcp import FastMCP  # requires: pip install mcp

logger = get_logger("products_server")

mcp = FastMCP("neobank-products-server")


@mcp.tool()
@trace(logger)
def list_loan_products(category: str | None = None) -> list[dict]:
    """List NeoBank India loan products, optionally filtered by category
    (personal, home, business, vehicle). Returns every product if category
    is omitted."""
    return database.list_loan_products(category=category)


@mcp.tool()
@trace(logger)
def get_loan_product_details(product_id: str) -> dict:
    """Look up full details (interest rate, max amount, minimum credit
    rating tolerance) for a single loan product by product_id."""
    product = database.get_loan_product(product_id)
    if not product:
        return {"error": f"No loan product found for product_id '{product_id}'"}
    return product


@mcp.tool()
@trace(logger)
def check_eligibility_criteria(product_id: str, applicant_risk_rating: str) -> dict:
    """Check whether a given risk_rating (low, medium, high -- as already
    determined by the compliance server) meets a product's minimum credit
    rating tolerance. This is a criteria check only, not a customer-specific
    lookup -- it takes risk_rating as an explicit argument rather than a
    customer_id, so this server never needs to see or store customer data.
    """
    product = database.get_loan_product(product_id)
    if not product:
        return {"error": f"No loan product found for product_id '{product_id}'"}

    rating_order = {"low": 0, "medium": 1, "high": 2}
    required = rating_order.get(product["min_credit_rating"], 2)
    applicant = rating_order.get(applicant_risk_rating, 2)

    eligible = applicant <= required
    reason = (
        f"applicant risk_rating '{applicant_risk_rating}' meets or exceeds "
        f"'{product['min_credit_rating']}' minimum for {product['name']}"
        if eligible else
        f"applicant risk_rating '{applicant_risk_rating}' does not meet the "
        f"'{product['min_credit_rating']}' minimum required for {product['name']}"
    )
    return {"product_id": product_id, "eligible": eligible, "reason": reason}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default=os.environ.get("MCP_TRANSPORT", "stdio"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", 8002)))
    parser.add_argument("--health-port", type=int, default=int(os.environ.get("HEALTH_PORT", 8012)))
    args = parser.parse_args()

    database.init_db(force=False)
    start_health_server("products_server", port=args.health_port)

    logger.info(f"Starting products_server via {args.transport} transport")
    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
    else:
        mcp.run(transport="stdio")
