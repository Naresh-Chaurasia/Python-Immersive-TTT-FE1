# BankForge — Architecture Document

**Capstone:** Week 5 — Model Context Protocol (Build, Compose & Deploy)
**Domain:** Digital banking — NeoBank India (fictional)
**Deliverable type:** Working MCP ecosystem + architecture document + deployment evidence + demo

---

## 1. System Overview

BankForge exposes NeoBank India's four disconnected backend systems (core
banking, loan/product catalogue, compliance/KYC, customer communication) to
any MCP-compatible AI client through **three MCP servers**, each
independently deployable, health-checked, and scoped to the minimum data
it needs.

```
                    ┌─────────────────────────────┐
                    │   AI Client (Claude         │
                    │   Desktop / API mcp_servers)│
                    └──────────┬─────────┬────────┘
                               │         │        │
                 ┌─────────────┘         │        └─────────────┐
                 ▼                       ▼                      ▼
┌────────────────────────┐   ┌───────────────────. ┐   ┌────────────────────────┐
│   accounts_server      │   │  products_server    │   │ compliance_comms_server│
│   (port 8001/8011)     │   │  (port 8002/8012)   │   │  (port 8003/8013)      │
│                        │   │                     │   │                        │
│  - get_account_        │   │ - list_loan_products│   │ - get_kyc_status       │
│    summary             │   │ - get_loan_product_ │   │ - run_compliance_check │
│  - get_accounts_for_   │   │   details           │   │ - send_customer_       │
│    customer            │   │ - check_eligibility_│   │   communication        │
│  - get_transaction_    │   │   criteria          │   │                        │
│    history             │   │                     │   │                        │
└────────────┬───────────┘   └──────────┬──────────┘   └──────────┬─────────────┘
                │                            │                            │
                └────────────────────────────┼────────────────────────────┘
                                             ▼
                                  ┌─────────────────────┐
                                  │  shared neobank.db  │
                                  │  (SQLite, WAL mode, │
                                  │ Docker named volume)│
                                  └─────────────────────┘
```

Every tool call across all three servers is traced (ENTER/EXIT, DEBUG
level, structured JSON) via `logging_config.trace()`, and every
PII-shaped argument is redacted before it reaches a log line via
`guardrails.redact_for_logging()`.

## 2. Why This 3-Server Split

The problem statement names five capability areas (account data,
transaction history, loan/product info, compliance/KYC, customer
communication) that must fit into three servers. The grouping:

| Server | Capabilities | Rationale |
|---|---|---|
| `accounts_server` | Account data + transaction history | Both read from the same core-banking tables and share the same scoped-access model (`caller_scope`) |
| `products_server` | Loan/product catalogue | Deliberately has **no access to customer or KYC data at all** — it takes `applicant_risk_rating` as an explicit argument rather than a `customer_id`, so eligibility criteria checks never require this server to see a real customer record. This is the least-privilege boundary made structural, not just policy. |
| `compliance_comms_server` | KYC/compliance rules + customer communication | Grouped together because every outbound communication needs a compliance check anyway — `send_customer_communication` enforces the KYC-based comms rule server-side, so the check can't be skipped by whichever client calls the tool |

## 3. Tool Inventory

| Server | Tool | Purpose |
|---|---|---|
| accounts_server | `get_account_summary(account_id, caller_scope)` | Account lookup, fields minimized per scope |
| accounts_server | `get_accounts_for_customer(customer_id, caller_scope)` | All accounts for a customer, same minimization |
| accounts_server | `get_transaction_history(account_id, limit)` | Recent transactions, most recent first |
| products_server | `list_loan_products(category)` | Catalogue browse, optional category filter |
| products_server | `get_loan_product_details(product_id)` | Single product lookup |
| products_server | `check_eligibility_criteria(product_id, applicant_risk_rating)` | Criteria check — no customer data touches this server |
| compliance_comms_server | `get_kyc_status(customer_id)` | The only tool anywhere that returns raw KYC data |
| compliance_comms_server | `run_compliance_check(customer_id, transaction_amount)` | Deterministic pass/block + large-transaction reporting flag |
| compliance_comms_server | `send_customer_communication(customer_id, channel, message)` | Sanitizes input, enforces KYC-based comms rule, logs the send |

## 4. Security & Compliance (graded criteria)

**Scoped access control.** Every accounts_server tool takes an explicit
`caller_scope` (`teller` / `loan_officer` / `compliance_officer` / `admin`).
`guardrails.minimize_account_fields()` strips fields the calling scope has
no business reason to see — a `teller` never receives `kyc_status` or
`risk_rating`, even though the underlying record has them.

> **Note on scoped access in production:** `caller_scope` is passed as an
> explicit tool argument here so the scoping *logic* is visible, testable,
> and gradeable without standing up a full auth stack. In a real deployment
> this would come from transport-level authentication (an API key or JWT
> mapped to a role by a gateway sitting in front of the MCP server) — the
> caller wouldn't get to just assert their own scope. Treat this as a
> teaching simplification, not the production security boundary itself.

**Data minimization.** Same mechanism as above — `minimize_account_fields`
is applied to every account record before it leaves `accounts_server`, and
`products_server` structurally never receives customer-identifying data at
all (see Section 2).

**Compliance checks — live, deterministic, demo-ready.**
`run_compliance_check` and `send_customer_communication` both make a real
rule-based decision, not an LLM-guessed one:
- Transactions above ₹50,000 are blocked outright for non-verified-KYC
  customers.
- Transactions ≥ ₹1,000,000 are flagged for large-transaction reporting.
- Marketing communications are blocked for any customer without verified
  KYC.

These rules live in `guardrails.py` as plain Python — no model call
anywhere in the decision path, so the outcome can't be changed by how a
request is phrased. `run_local_demo.py` exercises all three explicitly.

**Input sanitisation & prompt-injection defence.**
`guardrails.sanitize_free_text()` length-limits every message body, strips
HTML/markup, and screens for known injection signatures
(`"ignore all previous instructions"` and similar) before a communication
can be sent. A match raises rather than silently cleaning the text —
an attempted injection should stop the pipeline, not be laundered through.

**PII redaction in logs.** `guardrails.redact_for_logging()` is passed as
the `redact=` argument to every `@trace()` call on a tool that takes a
PII-shaped argument (`account_id`, `customer_id`, `phone`, `email`, etc.).
The ENTER log line still shows *that* an account_id was passed and its
length/shape (masked, e.g. `AC******45`), without exposing the real value —
log-based debugging stays possible without log-based data exposure.

## 5. Logging & Observability

Every function decorated with `@trace(logger)` emits:
- an **ENTER** line at DEBUG with a `call_id`, the function's fully
  qualified name, and its bound arguments (redacted if a `redact=`
  function was supplied)
- an **EXIT** line at DEBUG with the same `call_id`, a `duration_ms`, and
  a truncated preview of the return value
- on exception, a **FAILED** line at ERROR with the same `call_id`,
  `duration_ms`, the exception type, and a full traceback — then the
  exception is re-raised, so tracing never swallows an error

All three log types are structured JSON (`logging_config.JsonFormatter`),
one object per line, suitable for ingestion by any log aggregator.
`LOG_LEVEL` defaults to `DEBUG` everywhere and is overridable per
environment via the `LOG_LEVEL` env var.

## 6. Deployment Architecture

- Each server has its own `Dockerfile` (`docker/Dockerfile.accounts`,
  `.products`, `.compliance_comms`) built from a shared `requirements.txt`.
- `docker-compose.yml` orchestrates all three on a shared bridge network
  (`bankforge_net`), with a **named volume** (`neobank_data`) mounting the
  same SQLite file into all three containers so they see one consistent
  dataset.
- `products_server` and `compliance_comms_server` declare
  `depends_on: accounts_server: condition: service_healthy` —
  `accounts_server` seeds the database and passes its health check first,
  which effectively sequences database initialization before the other two
  start.
- Each container exposes two ports: the MCP server itself
  (`streamable-http` transport, e.g. `8001`) and a separate health-check
  HTTP endpoint (`8011`) run via the stdlib-only `health.py`, independent
  of whatever the MCP SDK's own transport does internally.
- `HEALTHCHECK` is declared both in each `Dockerfile` and mirrored in
  `docker-compose.yml`'s `healthcheck:` block.

## 7. Demo Script Mapping

| Rubric item | Where it's demonstrated |
|---|---|
| Scoped access | `run_local_demo.py` Section 1 — same account, `teller` vs `compliance_officer` views |
| Data minimization | Same section — `teller` response has no `kyc_status`/`risk_rating` keys at all |
| Live compliance check | `run_local_demo.py` Section 4 — large-transaction reporting flag + KYC-based block |
| Guardrails (input sanitisation, PII) | `run_local_demo.py` Section 5 — marketing-comms block + injection-signature block |
| Deployment evidence | `docker compose up --build`, then `curl localhost:8011/health` (and `:8012`, `:8013`) |
| Structured logging | Any terminal running a server with `LOG_LEVEL=DEBUG` (the default) — every call is traced |

## 8. Known Simplifications (be ready to name these in your demo debrief)

- **SQLite instead of Postgres.** Fine for a 3-container demo with WAL
  mode enabled; a real multi-service deployment would use a proper
  client-server database to avoid write-lock contention entirely.
- **`caller_scope` as an explicit argument** rather than derived from
  transport-level auth — see the callout in Section 4.
- **No real email/SMS delivery** — `send_customer_communication` logs a
  communication record; wiring an actual provider (SendGrid, Twilio) would
  replace `database.log_communication`'s body, not the guardrail logic
  around it.
