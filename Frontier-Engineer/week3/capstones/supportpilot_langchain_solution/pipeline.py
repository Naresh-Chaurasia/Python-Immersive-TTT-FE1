"""
SupportPilot (LangChain edition) — Pipeline orchestration.

Built from LangChain primitives: the classify/draft/validate steps are
LCEL chains (chains.py), the DB and KB lookups are LangChain Tools
(tools.py), and the account-lookup + knowledge-retrieval steps run
concurrently via RunnableParallel since neither depends on the other's
output. The escalation decision stays outside any chain — see
escalation_rules.py for why that's a deliberate choice, not an oversight.
"""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.runnables import RunnableLambda, RunnableParallel

import escalation_rules
from chains import classification_chain, drafting_chain, validation_chain
from tools import get_customer_tool, get_orders_tool, retrieve_kb_tool

try:
    from models import TicketClassification
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False


def _account_lookup(customer_id: str | None) -> dict | None:
    if not customer_id:
        return None
    customer = get_customer_tool.invoke({"customer_id": customer_id})
    if not customer:
        return None
    customer["recent_orders"] = get_orders_tool.invoke({"customer_id": customer_id})
    return customer


def _knowledge_retrieval(classification: dict) -> list[dict]:
    query = f"{classification['issue_type']} {classification['summary']}"
    return retrieve_kb_tool.invoke({"query": query})


def _relevant_order_amount(customer_ctx: dict | None, classification: dict) -> float:
    if not customer_ctx:
        return 0.0
    order_id = classification.get("extracted_order_id")
    orders = customer_ctx.get("recent_orders", [])
    if order_id:
        for o in orders:
            if o["order_id"].upper() == order_id.upper():
                return float(o["amount"])
    return float(orders[0]["amount"]) if orders else 0.0


# Account lookup and knowledge retrieval both depend only on the classification
# output, not on each other — RunnableParallel expresses that explicitly rather
# than hiding it in sequential code.
_context_gathering = RunnableParallel(
    customer_ctx=RunnableLambda(lambda x: _account_lookup(x["resolved_customer_id"])),
    kb_chunks=RunnableLambda(lambda x: _knowledge_retrieval(x["classification"])),
)


def run_ticket(ticket_id: str, ticket_text: str, customer_id: str | None = None) -> dict:
    trace: list[str] = []

    # 1. Classify
    classification = classification_chain.invoke({"ticket_id": ticket_id, "ticket_text": ticket_text})
    trace.append("classification_chain")

    if _PYDANTIC_AVAILABLE:
        classification = TicketClassification(**classification).model_dump()
        trace.append("pydantic_validation")

    resolved_customer_id = customer_id or classification.get("extracted_customer_id")

    # 2 & 3. Account lookup + knowledge retrieval, run via RunnableParallel
    context = _context_gathering.invoke({
        "resolved_customer_id": resolved_customer_id,
        "classification": classification,
    })
    customer_ctx, kb_chunks = context["customer_ctx"], context["kb_chunks"]
    trace.append("context_gathering (account_lookup_tool + retrieve_kb_tool, parallel)")

    # 4. Draft
    draft = drafting_chain.invoke({
        "classification": classification, "customer_ctx": customer_ctx, "kb_chunks": kb_chunks,
    })
    trace.append("drafting_chain")

    # 5. Validate
    validation = validation_chain.invoke({
        "draft": draft, "kb_chunks": kb_chunks, "classification": classification,
    })
    trace.append("validation_chain")

    # 6. Escalation decision — plain Python, no chain, no LLM. See escalation_rules.py.
    order_amount = _relevant_order_amount(customer_ctx, classification)
    validation_passed = validation["is_accurate"] and validation["is_on_policy"] and validation["tone_ok"]
    decision = escalation_rules.decide_escalation(
        issue_type=classification["issue_type"],
        sentiment=classification["sentiment"],
        urgency=classification["urgency"],
        confidence=classification["confidence"],
        validation_passed=validation_passed,
        order_amount=order_amount,
    )
    trace.append("escalation_rules (deterministic, no chain)")

    resolution_path = "escalated" if decision["should_escalate"] else "auto_resolved"
    final_response = None if decision["should_escalate"] else draft

    report = {
        "ticket_id": ticket_id,
        "classification": classification,
        "customer_context_found": customer_ctx is not None,
        "kb_chunks_used": [f"{c['source_doc']}#{c['section']}" for c in kb_chunks],
        "draft_response": draft,
        "validation": validation,
        "order_amount_considered": order_amount,
        "resolution_path": resolution_path,
        "final_response": final_response,
        "escalation": decision,
        "handled_at": datetime.now(timezone.utc).isoformat(),
        "agent_trace": trace + ["case_closure"],
    }
    return report


def pretty_print_report(report: dict) -> None:
    print(f"\n{'='*70}")
    print(f"Ticket: {report['ticket_id']}  |  Path: {report['resolution_path'].upper()}")
    print(f"{'='*70}")
    c = report["classification"]
    print(f"Issue type: {c['issue_type']} | Urgency: {c['urgency']} | Sentiment: {c['sentiment']} | Confidence: {c['confidence']:.2f}")
    print(f"KB chunks used: {report['kb_chunks_used'] or 'none'}")
    if report["resolution_path"] == "auto_resolved":
        print(f"Response: {report['final_response']}")
    else:
        esc = report["escalation"]
        print(f"ESCALATED — type: {esc['escalation_type']} | reason: {esc['reason']}")
    print(f"Agent trace: {' -> '.join(report['agent_trace'])}")


if __name__ == "__main__":
    report = run_ticket("T-DEMO-001", "Where is my order? It's been 6 days and tracking hasn't updated.", customer_id="CUST001")
    pretty_print_report(report)
