"""
SupportPilot (LangChain edition) — mode config + offline heuristics.

Same mock-mode heuristics as the original solution, kept here so
chains.py can wrap them in a RunnableLambda and the rest of the pipeline
never has to know whether it's talking to a real model or not.
"""
from __future__ import annotations

import os
import re

MODE = os.environ.get("SUPPORTPILOT_MODE", "mock")
MODEL = os.environ.get("SUPPORTPILOT_MODEL", "claude-sonnet-5")

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
    text = ticket_text.lower()
    word_count = len(text.split())
    default_confidence = 0.5 if word_count < 6 else 0.82
    issue_type, confidence = "general_inquiry", default_confidence

    for pattern, itype, conf in _KEYWORD_MAP:
        if re.search(pattern, text):
            issue_type, confidence = itype, conf
            break

    if re.search(_ANGRY_WORDS, text):
        sentiment = "angry"
    elif re.search(_FRUSTRATED_WORDS, text):
        sentiment = "frustrated"
    else:
        sentiment = "neutral"

    if issue_type in ("fraud_suspected", "complaint_escalation") or sentiment == "angry":
        urgency = "critical" if sentiment == "angry" else "high"
    elif issue_type in ("payment_issue", "damaged_item"):
        urgency = "high"
    else:
        urgency = "medium" if issue_type != "order_status" else "low"

    order_match = re.search(r"ORD\d{3,}", ticket_text, re.IGNORECASE)
    cust_match = re.search(r"CUST\d{3,}", ticket_text, re.IGNORECASE)

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

    return {
        "is_accurate": is_accurate,
        "is_on_policy": is_on_policy,
        "tone_ok": tone_ok,
        "issues_found": issues,
        "revised_response": None,
    }
