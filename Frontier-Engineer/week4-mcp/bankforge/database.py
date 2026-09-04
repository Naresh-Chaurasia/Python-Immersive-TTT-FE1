"""
BankForge — mock NeoBank India database.

Seeds a small SQLite database covering the four disconnected systems the
problem statement describes: core banking (customers/accounts/transactions),
loan/product catalogue, compliance/KYC, and a communication audit log.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from logging_config import get_logger, trace

logger = get_logger(__name__)

DB_PATH = Path(os.environ.get("NEOBANK_DB_PATH", str(Path(__file__).parent / "neobank.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    kyc_status TEXT,        -- verified | pending | rejected
    risk_rating TEXT,       -- low | medium | high
    segment TEXT            -- retail | small_business
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT,
    account_type TEXT,      -- savings | current | business
    balance REAL,
    status TEXT,            -- active | dormant | frozen
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT,
    amount REAL,
    direction TEXT,         -- credit | debit
    description TEXT,
    txn_date TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS loan_products (
    product_id TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,          -- personal | home | business | vehicle
    interest_rate REAL,
    max_amount REAL,
    min_credit_rating TEXT  -- low | medium | high -- minimum risk_rating tolerance
);

CREATE TABLE IF NOT EXISTS communications_log (
    comm_id TEXT PRIMARY KEY,
    customer_id TEXT,
    channel TEXT,
    message_preview TEXT,   -- first 50 chars only -- data minimization applied at write time
    status TEXT,
    sent_at TEXT
);
"""

CUSTOMERS = [
    ("CUST001", "Ananya Rao", "ananya.rao@example.com", "9800000001", "verified", "low", "retail"),
    ("CUST002", "Vikram Shah", "vikram.shah@example.com", "9800000002", "verified", "low", "business"),
    ("CUST003", "Priya Nair", "priya.nair@example.com", "9800000003", "pending", "medium", "retail"),
    ("CUST004", "Rohan Mehta", "rohan.mehta@example.com", "9800000004", "verified", "high", "retail"),
    ("CUST005", "Sneha Iyer", "sneha.iyer@example.com", "9800000005", "verified", "low", "business"),
    ("CUST006", "Arjun Kapoor", "arjun.kapoor@example.com", "9800000006", "rejected", "high", "retail"),
]

ACCOUNTS = [
    ("ACC0001", "CUST001", "savings", 85000.0, "active"),
    ("ACC0002", "CUST002", "business", 1250000.0, "active"),
    ("ACC0003", "CUST003", "savings", 12000.0, "active"),
    ("ACC0004", "CUST004", "current", 500.0, "dormant"),
    ("ACC0005", "CUST005", "business", 340000.0, "active"),
    ("ACC0006", "CUST006", "savings", 0.0, "frozen"),
]

TRANSACTIONS = [
    ("TXN0001", "ACC0001", 15000.0, "credit", "Salary credit", "2025-11-01"),
    ("TXN0002", "ACC0001", 2000.0, "debit", "ATM withdrawal", "2025-11-03"),
    ("TXN0003", "ACC0002", 1050000.0, "credit", "Client payment received", "2025-11-05"),
    ("TXN0004", "ACC0002", 300000.0, "debit", "Supplier payment", "2025-11-06"),
    ("TXN0005", "ACC0003", 500.0, "debit", "UPI payment", "2025-11-07"),
    ("TXN0006", "ACC0005", 75000.0, "credit", "Invoice settlement", "2025-11-08"),
]

LOAN_PRODUCTS = [
    ("LOAN_PERSONAL_01", "NeoBank Personal Loan", "personal", 11.5, 500000.0, "medium"),
    ("LOAN_HOME_01", "NeoBank Home Loan", "home", 8.4, 7500000.0, "low"),
    ("LOAN_BUSINESS_01", "NeoBank Business Growth Loan", "business", 12.0, 2000000.0, "medium"),
    ("LOAN_VEHICLE_01", "NeoBank Vehicle Loan", "vehicle", 9.8, 1000000.0, "medium"),
]


@trace(logger)
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")  # reduces lock contention across the 3 server processes
    return conn


@trace(logger)
def init_db(force: bool = False) -> None:
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    conn.executescript(SCHEMA)
    conn.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)", CUSTOMERS)
    conn.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?,?,?)", ACCOUNTS)
    conn.executemany("INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?)", TRANSACTIONS)
    conn.executemany("INSERT OR IGNORE INTO loan_products VALUES (?,?,?,?,?,?)", LOAN_PRODUCTS)
    conn.commit()
    conn.close()


@trace(logger)
def get_account(account_id: str) -> dict | None:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


@trace(logger)
def get_accounts_for_customer(customer_id: str) -> list[dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM accounts WHERE customer_id = ?", (customer_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@trace(logger)
def get_transactions(account_id: str, limit: int = 10) -> list[dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM transactions WHERE account_id = ? ORDER BY txn_date DESC LIMIT ?",
        (account_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@trace(logger)
def get_customer(customer_id: str) -> dict | None:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


@trace(logger)
def list_loan_products(category: str | None = None) -> list[dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    if category:
        rows = conn.execute("SELECT * FROM loan_products WHERE category = ?", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM loan_products").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@trace(logger)
def get_loan_product(product_id: str) -> dict | None:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM loan_products WHERE product_id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


@trace(logger)
def log_communication(comm_id: str, customer_id: str, channel: str, message: str, status: str, sent_at: str) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO communications_log VALUES (?,?,?,?,?,?)",
        (comm_id, customer_id, channel, message[:50], status, sent_at),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db(force=True)
    print(f"Seeded {DB_PATH}")
    print(f"Customers: {len(CUSTOMERS)} | Accounts: {len(ACCOUNTS)} | "
          f"Transactions: {len(TRANSACTIONS)} | Loan products: {len(LOAN_PRODUCTS)}")
