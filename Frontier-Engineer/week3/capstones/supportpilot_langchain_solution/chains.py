"""
SupportPilot (LangChain edition) — Chains (Week 2, Section 1.4: "LangChain
Foundations" — prompt templates, chaining, output parsers).

Each function below returns a LangChain Runnable. In `mock` mode that's a
RunnableLambda wrapping the offline heuristics in mock_heuristics.py — so
the pipeline's shape (a sequence of .invoke() calls) is identical whether
you're offline or hitting a real model. In `live` mode it's a real
ChatPromptTemplate | ChatAnthropic | <parser> chain using structured
output bound to the Pydantic models in models.py.
"""
from __future__ import annotations

import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

import mock_heuristics as mock
from mock_heuristics import MODE, MODEL
from models import TicketClassification, ValidationResult


def _get_chat_model():
    from langchain_anthropic import ChatAnthropic  # imported lazily, live mode only
    return ChatAnthropic(model=MODEL, max_tokens=1000)


# ---------------------------------------------------------------------------
# 1. Classification chain
# ---------------------------------------------------------------------------

def build_classification_chain():
    if MODE == "mock":
        return RunnableLambda(lambda inputs: mock.mock_classify(inputs["ticket_id"], inputs["ticket_text"]))

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You classify ShopStream India customer support tickets accurately and conservatively. "
         "If the ticket is ambiguous, reflect that with a lower confidence score rather than guessing."),
        ("human", "ticket_id: {ticket_id}\nticket_text: {ticket_text}"),
    ])
    llm = _get_chat_model().with_structured_output(TicketClassification)
    return prompt | llm | RunnableLambda(lambda result: result.model_dump())


# ---------------------------------------------------------------------------
# 2. Drafting chain
# ---------------------------------------------------------------------------

def build_drafting_chain():
    if MODE == "mock":
        return RunnableLambda(lambda inputs: mock.mock_draft(
            inputs["classification"], inputs["customer_ctx"], inputs["kb_chunks"]
        ))

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You draft ShopStream India customer support responses. Ground every factual claim "
         "ONLY in the provided kb_chunks and customer context. Never invent a policy detail. "
         "Be concise, and lead with empathy if the customer's sentiment is frustrated or angry."),
        ("human",
         "classification: {classification}\ncustomer_context: {customer_ctx}\nkb_chunks: {kb_chunks}"),
    ])
    llm = _get_chat_model()
    return prompt | llm | StrOutputParser()


# ---------------------------------------------------------------------------
# 3. Validation chain
# ---------------------------------------------------------------------------

def build_validation_chain():
    if MODE == "mock":
        return RunnableLambda(lambda inputs: mock.mock_validate(
            inputs["draft"], inputs["kb_chunks"], inputs["classification"]
        ))

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a strict QA validator for customer support drafts. Check: (1) every factual "
         "claim is grounded in kb_chunks, (2) nothing promised exceeds stated policy, (3) tone "
         "matches the customer's sentiment. Be conservative — when unsure, fail the check."),
        ("human", "draft: {draft}\nkb_chunks: {kb_chunks}\nclassification: {classification}"),
    ])
    llm = _get_chat_model().with_structured_output(ValidationResult)
    return prompt | llm | RunnableLambda(lambda result: result.model_dump())


# Build once, reuse across tickets (mirrors building an index once in Week 3)
classification_chain = build_classification_chain()
drafting_chain = build_drafting_chain()
validation_chain = build_validation_chain()
