"""
SupportPilot — Agent functions.

Each function is one agent's responsibility, kept small and single-purpose
so the pipeline in pipeline.py can trace exactly which agent produced what.
"""
from __future__ import annotations

import database
import llm_client
from logging_config import get_logger
from retrieval import KnowledgeRetriever

logger = get_logger(__name__)

_retriever = KnowledgeRetriever()


def classifier_agent(ticket_id: str, ticket_text: str) -> dict:
    result = llm_client.classify_ticket(ticket_id, ticket_text)
    logger.info(
        "Classified %s -> issue=%s urgency=%s sentiment=%s confidence=%.2f",
        ticket_id, result["issue_type"], result["urgency"], result["sentiment"], result["confidence"],
    )
    return result


def account_lookup_agent(customer_id: str | None) -> dict | None:
    if not customer_id:
        logger.info("Account lookup skipped: no customer_id available")
        return None
    customer = database.get_customer(customer_id)
    if not customer:
        logger.info("Account lookup: %s not found", customer_id)
        return None
    orders = database.get_orders(customer_id)
    customer["recent_orders"] = orders
    customer["prior_ticket_count"] = database.get_prior_ticket_count(customer_id)
    logger.info(
        "Account lookup: %s found (%s, %d order(s), %d prior ticket(s))",
        customer_id, customer["account_standing"], len(orders), customer["prior_ticket_count"],
    )
    return customer


def knowledge_retrieval_agent(query: str, top_k: int = 3) -> list[dict]:
    results = _retriever.retrieve(query, top_k=top_k)
    logger.info("Knowledge retrieval: %d chunk(s) found for query '%s'", len(results), query)
    return results


def drafting_agent(classification: dict, customer_ctx: dict | None, kb_chunks: list[dict]) -> str:
    draft = llm_client.draft_response(classification, customer_ctx, kb_chunks)
    logger.info("Draft response generated (%d chars)", len(draft))
    return draft


def validation_agent(draft: str, kb_chunks: list[dict], classification: dict) -> dict:
    result = llm_client.validate_response(draft, kb_chunks, classification)
    passed = result["is_accurate"] and result["is_on_policy"] and result["tone_ok"]
    logger.info("Validation %s (%d issue(s) found)", "PASSED" if passed else "FAILED", len(result["issues_found"]))
    return result


def get_relevant_order_amount(customer_ctx: dict | None, classification: dict) -> float:
    """Best-effort lookup of the order amount relevant to a refund/payment ticket,
    used by the escalation gate's high-value-refund rule."""
    if not customer_ctx:
        return 0.0
    order_id = classification.get("extracted_order_id")
    orders = customer_ctx.get("recent_orders", [])
    if order_id:
        for o in orders:
            if o["order_id"].upper() == order_id.upper():
                return float(o["amount"])
    # fall back to the most recent order if no specific order was referenced
    return float(orders[0]["amount"]) if orders else 0.0
