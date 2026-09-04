"""Tests for database.py. Run with: python3 -m pytest tests/ -v"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import database


@pytest.fixture(autouse=True)
def seeded_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_neobank.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db(force=True)
    yield


def test_get_account_returns_expected_fields():
    account = database.get_account("ACC0001")
    assert account["account_id"] == "ACC0001"
    assert account["customer_id"] == "CUST001"
    assert account["status"] == "active"


def test_get_account_unknown_id_returns_none():
    assert database.get_account("ACC9999") is None


def test_get_transactions_respects_limit():
    txns = database.get_transactions("ACC0002", limit=1)
    assert len(txns) == 1


def test_get_transactions_ordered_most_recent_first():
    txns = database.get_transactions("ACC0002", limit=10)
    dates = [t["txn_date"] for t in txns]
    assert dates == sorted(dates, reverse=True)


def test_list_loan_products_filters_by_category():
    business_products = database.list_loan_products(category="business")
    assert all(p["category"] == "business" for p in business_products)
    assert len(business_products) >= 1


def test_log_communication_truncates_message_preview():
    long_message = "x" * 500
    database.log_communication("COMM-TEST", "CUST001", "email", long_message, "sent", "2025-11-01T00:00:00Z")
    conn = database._connect()
    row = conn.execute("SELECT message_preview FROM communications_log WHERE comm_id = ?", ("COMM-TEST",)).fetchone()
    conn.close()
    assert len(row[0]) == 50
