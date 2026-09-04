"""
SupportPilot — LLM client.

Two modes:
  - mock  (default): deterministic, keyword-based heuristics standing in
    for the LLM calls. Lets the whole pipeline run offline, with no API
    key, for fast iteration and CI-style testing.
  - live: real calls to the Anthropic API. Set SUPPORTPILOT_MODE=live
    and ANTHROPIC_API_KEY in your environment.

Swap MODE to "live" once your agents are wired up and you want to test
against a real model. Keep mock mode around — it's what makes your test
suite fast and deterministic for the demo.
"""
from __future__ import annotations

import json
import os
import re

from logging_config import get_logger

logger = get_logger(__name__)

MODE = os.environ.get("SUPPORTPILOT_MODE", "mock")
MODEL = os.environ.get("SUPPORTPILOT_MODEL", "claude-sonnet-5")
logger.info("LLM client mode: %s%s", MODE, f" (model={MODEL})" if MODE == "live" else "")


def _live_client():
    import anthropic  # imported lazily so mock mode never requires the package
    if "ANTHROPIC_API_KEY" not in os.environ:
        logger.error("SUPPORTPILOT_MODE=live but ANTHROPIC_API_KEY is not set")
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required in live mode")
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _call_live(system: str, user: str, max_tokens: int = 1000) -> str:
    logger.debug("Calling live LLM (%s, max_tokens=%d)", MODEL, max_tokens)
    client = _live_client()
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception:
        logger.exception("Live LLM call failed (model=%s)", MODEL)
        raise
    text = "".join(block.text for block in resp.content if block.type == "text")
    logger.debug("Live LLM response (%d chars)", len(text))
    return text


# ---------------------------------------------------------------------------
# Mock-mode heuristics (offline, deterministic, no network / no API key)
# ---------------------------------------------------------------------------

_KEYWORD_MAP = [
    (r"don'?t recognize|didn'?t make this|unauthorized transaction|not my transaction|"
     r"not sure (it|this) was me|wasn'?t me|not sure i made|don'?t think i made|"
     r"(double check|make sure).*(charge|transaction)", "fraud_suspected", 0.9),
    (r"charged twice|double charged|duplicate charge", "payment_issue", 0.9),
    (r"payment failed|money (was )?deducted|debited but", "payment_issue", 0.85),
    (r"manager|legal action|consumer court|media|news", "complaint_escalation", 0.9),
    (r"refund", "refund_request", 0.85),
    (r"damaged|broken|defective", "damaged_item", 0.85),
    (r"where is my order|track my order|order status|not delivered yet", "order_status", 0.9),
    (r"locked out|can'?t log ?in|reset password|account access", "account_access", 0.85),
]

_ANGRY_WORDS = r"furious|unacceptable|ridiculous|scam|worst|disgusted|angry"
_FRUSTRATED_WORDS = r"frustrat|annoyed|disappointed|not happy"


def mock_classify(ticket_id: str, ticket_text: str) -> dict:
    logger.info("Classify %s: input=%r", ticket_id, ticket_text)
    text = ticket_text.lower()
    word_count = len(text.split())
    # A clear, well-formed sentence that just doesn't match a known category is a
    # legitimate general inquiry (higher confidence). A very short/vague ticket is
    # genuinely ambiguous and should go through the low-confidence escalation gate.
    default_confidence = 0.5 if word_count < 6 else 0.82
    issue_type, confidence = "general_inquiry", default_confidence
    logger.info(
        "Classify %s: step 1/5 baseline -> word_count=%d, default issue_type=general_inquiry, confidence=%.2f (%s)",
        ticket_id, word_count, default_confidence,
        "short ticket, low confidence" if word_count < 6 else "long enough to trust as a real inquiry",
    )

    for pattern, itype, conf in _KEYWORD_MAP:
        if re.search(pattern, text):
            issue_type, confidence = itype, conf
            logger.info(
                "Classify %s: step 2/5 keyword scan -> matched pattern for issue_type=%s (confidence=%.2f)",
                ticket_id, itype, conf,
            )
            break
    else:
        logger.info("Classify %s: step 2/5 keyword scan -> no pattern matched, keeping default general_inquiry", ticket_id)

    if re.search(_ANGRY_WORDS, text):
        sentiment = "angry"
    elif re.search(_FRUSTRATED_WORDS, text):
        sentiment = "frustrated"
    else:
        sentiment = "neutral"
    logger.info("Classify %s: step 3/5 sentiment scan -> sentiment=%s", ticket_id, sentiment)

    if issue_type in ("fraud_suspected", "complaint_escalation") or sentiment == "angry":
        urgency = "critical" if sentiment == "angry" else "high"
        reason = "angry sentiment" if sentiment == "angry" else f"issue_type={issue_type} is always high/critical urgency"
    elif issue_type in ("payment_issue", "damaged_item"):
        urgency = "high"
        reason = f"issue_type={issue_type} is always high urgency"
    else:
        urgency = "medium" if issue_type != "order_status" else "low"
        reason = "default urgency for this issue_type"
    logger.info("Classify %s: step 4/5 urgency decision -> urgency=%s (%s)", ticket_id, urgency, reason)

    order_match = re.search(r"ORD\d{3,}", ticket_text, re.IGNORECASE)
    cust_match = re.search(r"CUST\d{3,}", ticket_text, re.IGNORECASE)
    logger.info(
        "Classify %s: step 5/5 ID extraction -> order_id=%s, customer_id=%s",
        ticket_id,
        order_match.group(0).upper() if order_match else "none found",
        cust_match.group(0).upper() if cust_match else "none found",
    )

    return {
        "ticket_id": ticket_id,
        "issue_type": issue_type,
        "urgency": urgency,
        "sentiment": sentiment,
        "confidence": confidence,
        "extracted_order_id": order_match.group(0).upper() if order_match else None,
        "extracted_customer_id": cust_match.group(0).upper() if cust_match else None,
        "summary": ticket_text.strip()[:140],
    }


def mock_draft(classification: dict, customer_ctx: dict | None, kb_chunks: list[dict]) -> str:
    name = customer_ctx["name"].split()[0] if customer_ctx else "there"
    opener = "I'm really sorry for the trouble here" if classification["sentiment"] in ("angry", "frustrated") else "Thanks for reaching out"
    if kb_chunks:
        policy_line = f" Based on our policy ({kb_chunks[0]['source_doc'].replace('_', ' ').replace('.md','')}): {kb_chunks[0]['text'].splitlines()[-1].strip()}"
    else:
        policy_line = " I don't have a specific policy reference for this yet, so I'll have a specialist confirm the exact next step."
    logger.debug("mock_draft: grounded=%s, opener='%s'", bool(kb_chunks), opener)
    return f"Hi {name}, {opener}.{policy_line} Let us know if you have further questions."


def mock_validate(draft: str, kb_chunks: list[dict], classification: dict) -> dict:
    issues = []
    is_accurate = True
    is_on_policy = True
    tone_ok = True

    if not kb_chunks and classification["issue_type"] not in ("general_inquiry", "order_status"):
        is_accurate = False
        issues.append("No grounding KB chunks retrieved for a policy-dependent issue type")

    if "sorry" not in draft.lower() and classification["sentiment"] in ("angry", "frustrated"):
        tone_ok = False
        issues.append("Missing empathetic opening for a frustrated/angry customer")

    if re.search(r"\bguarantee\b|\bpromise\b", draft.lower()):
        is_on_policy = False
        issues.append("Draft uses absolute language ('guarantee'/'promise') not supported by policy wording")

    if issues:
        logger.debug("mock_validate: issues=%s", issues)

    return {
        "is_accurate": is_accurate,
        "is_on_policy": is_on_policy,
        "tone_ok": tone_ok,
        "issues_found": issues,
        "revised_response": None,
    }


# ---------------------------------------------------------------------------
# Public functions used by agents.py — route to mock or live based on MODE
# ---------------------------------------------------------------------------

def _parse_live_json(raw: str, context: str) -> dict:
    """Parse a live LLM's JSON reply, logging clearly if it comes back malformed."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Live LLM returned non-JSON response for %s: %r", context, raw)
        raise


def classify_ticket(ticket_id: str, ticket_text: str) -> dict:
    if MODE == "mock":
        return mock_classify(ticket_id, ticket_text)
    logger.debug("classify_ticket %s: routing to live LLM", ticket_id)
    system = (
        "You classify ShopStream India customer support tickets. Respond ONLY with JSON matching: "
        '{"ticket_id": str, "issue_type": one of [order_status, refund_request, damaged_item, '
        'payment_issue, account_access, fraud_suspected, general_inquiry, complaint_escalation], '
        '"urgency": one of [low, medium, high, critical], "sentiment": one of [neutral, frustrated, angry, satisfied], '
        '"confidence": float 0-1, "extracted_order_id": str or null, "extracted_customer_id": str or null, "summary": str}'
    )
    raw = _call_live(system, f"ticket_id: {ticket_id}\nticket_text: {ticket_text}")
    return _parse_live_json(raw, f"classify_ticket({ticket_id})")


def draft_response(classification: dict, customer_ctx: dict | None, kb_chunks: list[dict]) -> str:
    if MODE == "mock":
        return mock_draft(classification, customer_ctx, kb_chunks)
    logger.debug("draft_response: routing to live LLM")
    system = (
        "You draft ShopStream India customer support responses. Ground every factual claim in the "
        "provided context only. Do not invent policy details. Keep it concise and empathetic."
    )
    user = json.dumps({"classification": classification, "customer": customer_ctx, "kb_chunks": kb_chunks})
    return _call_live(system, user)


def validate_response(draft: str, kb_chunks: list[dict], classification: dict) -> dict:
    if MODE == "mock":
        return mock_validate(draft, kb_chunks, classification)
    logger.debug("validate_response: routing to live LLM")
    system = (
        "You are a QA validator for customer support drafts. Check groundedness against kb_chunks, "
        "policy compliance, and tone appropriateness. Respond ONLY with JSON matching: "
        '{"is_accurate": bool, "is_on_policy": bool, "tone_ok": bool, "issues_found": [str], "revised_response": str or null}'
    )
    user = json.dumps({"draft": draft, "kb_chunks": kb_chunks, "classification": classification})
    raw = _call_live(system, user)
    return _parse_live_json(raw, "validate_response")
