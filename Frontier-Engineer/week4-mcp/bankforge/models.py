"""
BankForge — Pydantic schemas shared across the three MCP servers.

Note: pydantic isn't installed in every environment this was developed in
(see README's testing note) -- these models were written against standard
Pydantic v2 syntax but should be verified with `pip install pydantic` in
your own environment before relying on them.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# accounts_server
# ---------------------------------------------------------------------------

class AccountSummary(BaseModel):
    account_id: str
    customer_id: str
    account_type: Literal["savings", "current", "business"]
    balance: float
    status: Literal["active", "dormant", "frozen"]
    kyc_status: Optional[str] = None
    risk_rating: Optional[str] = None


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    direction: Literal["credit", "debit"]
    description: str
    txn_date: str


# ---------------------------------------------------------------------------
# products_server
# ---------------------------------------------------------------------------

class LoanProduct(BaseModel):
    product_id: str
    name: str
    category: Literal["personal", "home", "business", "vehicle"]
    interest_rate: float
    max_amount: float
    min_credit_rating: Literal["low", "medium", "high"]


class LoanEligibilityResult(BaseModel):
    product_id: str
    eligible: bool
    reason: str


# ---------------------------------------------------------------------------
# compliance_comms_server
# ---------------------------------------------------------------------------

class KYCStatus(BaseModel):
    customer_id: str
    kyc_status: Literal["verified", "pending", "rejected"]
    risk_rating: Literal["low", "medium", "high"]


class ComplianceCheckResult(BaseModel):
    customer_id: str
    check_type: str
    passed: bool
    requires_reporting: bool = False
    details: str


class CommunicationRequest(BaseModel):
    customer_id: str
    channel: Literal["email", "sms", "marketing"]
    message: str = Field(max_length=2000)


class CommunicationResult(BaseModel):
    comm_id: str
    status: Literal["sent", "blocked"]
    reason: str
