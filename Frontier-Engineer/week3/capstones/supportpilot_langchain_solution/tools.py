"""
SupportPilot (LangChain edition) — Tools (Week 3-4: "converting Python
functions into custom tools").

These are real LangChain `@tool`-decorated functions with typed args and
docstrings the tool schema is generated from. The deterministic pipeline
in pipeline.py calls them directly via `.invoke(...)` (not through an
autonomous tool-picking agent loop) — the ticket workflow's step order is
fixed by design, so nothing here should be left to a model's discretion
about *which* tool to call next. Wrapping them as LangChain Tools still
pays off: it's what you'd hand to an AutoGen/CrewAI agent in Week 4's
looser orchestration, or expose via an MCP server in Week 5, with zero
extra work.
"""
from __future__ import annotations

from langchain_core.tools import tool

import database
from retrieval import KnowledgeRetriever

_retriever = KnowledgeRetriever()


@tool
def get_customer_tool(customer_id: str) -> dict:
    """Look up a ShopStream India customer's profile by customer_id (e.g. CUST001)."""
    return database.get_customer(customer_id) or {}


@tool
def get_orders_tool(customer_id: str) -> list[dict]:
    """Look up a ShopStream India customer's order history by customer_id."""
    return database.get_orders(customer_id)


@tool
def retrieve_kb_tool(query: str) -> list[dict]:
    """Search ShopStream India's customer-facing policy knowledge base for
    relevant sections (refunds, shipping/damage, payments, account recovery)."""
    return _retriever.retrieve(query, top_k=3)


@tool
def retrieve_internal_kb_tool(query: str) -> list[dict]:
    """Search the internal-only escalation criteria document. Never surface
    results from this tool directly to a customer."""
    return _retriever.retrieve_internal(query, top_k=2)
