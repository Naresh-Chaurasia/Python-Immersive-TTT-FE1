# SupportPilot — LangChain Edition

Same system as the original SupportPilot solution — classify -> account
lookup + KB retrieval -> draft -> validate -> escalate -> case report —
rebuilt on top of LangChain primitives instead of plain function calls.

## What changed vs. the original solution

| Piece | Original | LangChain edition |
|---|---|---|
| Classify / Draft / Validate | Python functions in `llm_client.py` | LCEL chains (`ChatPromptTemplate \| ChatAnthropic \| parser`) in `chains.py` |
| Knowledge retrieval | Custom TF-IDF class in `retrieval.py` | `FAISS.from_documents()` + `.as_retriever()`, backed by a LangChain `Embeddings` implementation |
| DB / KB access | Plain functions | `@tool`-decorated LangChain Tools in `tools.py` |
| Orchestration | Sequential Python calls | LCEL `RunnableParallel` for the two independent lookups, `.invoke()` chaining for the rest |
| Escalation logic | Plain Python | **Unchanged, deliberately.** See "Why escalation stays outside LangChain" below. |
| Database, models, KB docs, escalation rules | — | **Unchanged, reused as-is** — no need to touch what already worked |

## Quick start

```bash
pip install -r requirements.txt
python3 main.py --init-db
python3 main.py --test-suite
python3 main.py --ticket "Where is my order?" --customer CUST001 --json
```

Defaults to **mock mode** (no API key, no network) — same as before.
Set `SUPPORTPILOT_MODE=live` and `ANTHROPIC_API_KEY` to route the chains
through a real `ChatAnthropic` model.

## Project layout

```
supportpilot_langchain/
├── models.py             Pydantic schemas (unchanged from original)
├── database.py           Mock SQLite DB (unchanged from original)
├── escalation_rules.py   Deterministic escalation gates (unchanged from original)
├── embeddings.py         Offline TF-IDF Embeddings class (LangChain Embeddings interface)
├── retrieval.py          FAISS vector store + retriever over kb/*.md
├── tools.py              @tool-decorated DB and KB lookup tools
├── chains.py             LCEL chains for classify / draft / validate (mock + live)
├── mock_heuristics.py    The offline heuristics the mock chains wrap
├── pipeline.py           Orchestrates chains + tools into the full ticket flow
├── test_tickets.py       Same 8 scenarios as the original solution
├── main.py               CLI
├── kb/                   Same 5 policy markdown docs
└── requirements.txt
```

## Why escalation stays outside LangChain

`escalation_rules.py` is untouched on purpose. It's plain Python `if`
statements with no chain, no tool, no model call — because the whole
point of the hard-category gate (fraud, duplicate charges, high-value
refunds, explicit "get me a manager" requests) is that it must fire the
same way no matter how the ticket is phrased. Wrapping it in a chain
would mean a prompt is involved somewhere in the decision, which is
exactly the surface a rephrased ticket could exploit. Keep this logic
boring and deterministic; that's the safety property the capstone rubric
is actually testing for. `test_tickets.py` cases 4 and 5 (same fraud
report, one blunt, one hedged) both need to escalate — that's the check.

## Why retrieval uses a custom offline Embeddings class

`FAISS.from_documents()` needs an `Embeddings` object, and the standard
choices (`OpenAIEmbeddings`, `HuggingFaceEmbeddings`) either need an API
key or a model download — both awkward in a locked-down training
environment. `embeddings.py` implements the same `Embeddings` interface
(`embed_documents` / `embed_query`) using scikit-learn's TF-IDF instead,
so the FAISS store builds with zero network calls. If your environment
has internet access and you'd rather use real semantic embeddings, this
is a one-line swap in `retrieval.py`:

```python
from langchain_community.embeddings import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
```

Nothing else in `retrieval.py`, `tools.py`, or `pipeline.py` needs to
change — that's the point of coding against the `Embeddings` interface.

## A note on testing in this environment

`langchain`, `langchain-community`, and `langchain-anthropic` are not
installed in the sandbox this was built in (no network access to `pip
install` them), so `chains.py`, `pipeline.py`, `tools.py`, `retrieval.py`,
and `embeddings.py` were written carefully against the current LangChain
API and syntax-checked (`python3 -m py_compile`), but **not executed
end-to-end** here. `database.py`, `escalation_rules.py`, and `models.py`
are unchanged carryovers from the original solution, which *was* fully
tested (8/8 scenarios passing).

Before your demo:
```bash
pip install -r requirements.txt
python3 main.py --init-db
python3 main.py --test-suite
```
If any import errors show up, they're most likely due to LangChain's
fast-moving API (module paths for `FAISS`/`Embeddings` have moved between
`langchain`, `langchain_community`, and provider-specific packages a few
times) — check the version installed against LangChain's own migration
guide and adjust the import path, the logic underneath won't need to
change.

## Extending further

- Swap `chains.py`'s plain LCEL sequencing for a `SelectorGroupChat`-style
  dynamic router (Week 4) if you want the system to decide which agent
  runs next based on ticket content, rather than a fixed sequence.
- Wrap `tools.py`'s tools behind an MCP server (Week 5) instead of calling
  them directly — this is a very small step from here, since they're
  already framework-native Tool objects.
