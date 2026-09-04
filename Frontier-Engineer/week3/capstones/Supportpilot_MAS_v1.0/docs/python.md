# Python skills needed for SupportPilot

A guide to the Python knowledge required to read, understand, and run this
project. Grouped from "must know to run it" up to "helps you extend it."

## 1. Running things (bare minimum)

- **Virtual environments & pip** — `pip install -r requirements.txt` to get
  scikit-learn, numpy, pydantic, and anthropic.
- **Running a script** — `python main.py ...`; know the difference between
  running a file vs importing it.
- **Environment variables** — `SUPPORTPILOT_MODE`, `ANTHROPIC_API_KEY`,
  `SUPPORTPILOT_MODEL` switch mock vs live mode (read via `os.environ`).

## 2. Core language

- **Functions & parameters** — every agent is a plain function with keyword
  args and defaults (e.g. `run_ticket(ticket_id, ticket_text, customer_id=None)`).
- **Data structures** — dicts, lists, and lists-of-dicts are the main data
  carriers (classification dict, KB chunks, the final report).
- **f-strings & string formatting** — building KB queries and report output.
- **Comprehensions** — e.g. `[dict(r) for r in rows]`, list building in
  `database.py`.
- **Truthiness & `None` handling** — `customer_id or classification.get(...)`,
  `customer_ctx is not None`.
- **`if __name__ == "__main__":`** — every module has a runnable demo block.

## 3. Modules & typing

- **Imports & modules** — the project is many small modules importing each
  other (`import agents`, `import escalation_rules`); no package framework.
- **`try/except ImportError`** — optional dependency pattern that lets the
  pipeline run even if Pydantic isn't installed (`pipeline.py`).
- **Type hints** — modern syntax like `dict | None`, `list[dict]`, plus
  `from __future__ import annotations`. Read-only; they don't affect runtime.

## 4. Standard library used here

- **`sqlite3`** — connect, `execute` / `executemany`, `row_factory`,
  parameterised queries (`?` placeholders) in `database.py`.
- **`argparse`** — the CLI flags in `main.py` (`--init-db`, `--ticket`, etc.).
- **`json`** — pretty-printing the case report (`--json`).
- **`pathlib.Path`** — locating the DB file and `kb/` docs.
- **`datetime` / `timezone`** — timestamping the report.
- **`re` (regex)** — mock-mode classification in `llm_client.py`.

## 5. Third-party libraries (concepts, not deep expertise)

- **Pydantic v2** — `BaseModel` schemas and `.model_dump()` for the
  structured-intake validation gate (`models.py`).
- **scikit-learn** — `TfidfVectorizer` + cosine similarity for the knowledge
  retriever (`retrieval.py`). You only need the idea: turn text into vectors,
  score similarity.
- **anthropic** — the Messages API client, used only in live mode
  (`llm_client.py`). Not needed for mock mode.

## 6. Nice to have (for extending)

- **Design patterns** — sequential pipeline / orchestration; each agent maps
  1:1 to an Agent+Task if you later swap in CrewAI/AutoGen.
- **Basic testing mindset** — `test_tickets.py` runs scenarios and asserts the
  expected resolution path; understanding pass/fail checks helps you add cases.
- **Regex** — to tune or extend the mock classifier heuristics.

## Quick self-check

If you can answer these, you know enough to work on this project:
1. What's the difference between mock and live mode, and how do you switch?
2. Why does `pipeline.py` wrap the Pydantic import in `try/except`?
3. How does `database.py` avoid SQL injection in its queries?
4. Where would you add a new issue category, and what would you change?
