"""
SupportPilot (LangChain edition) — Knowledge Retrieval, built on LangChain's
document/vectorstore/retriever abstractions (Week 3: Sections 2.3-2.4).

Pipeline: load markdown -> split into section-level chunks -> embed -> FAISS
index -> `.as_retriever()`. The internal-only escalation_criteria.md is kept
in a *separate* FAISS index so the customer-facing retriever can never
surface it, while the escalation agent can still query it directly for
grounding.
"""
from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from embeddings import LocalTfidfEmbeddings

KB_DIR = Path(__file__).parent / "kb"
INTERNAL_DOC = "escalation_criteria.md"


def _load_section_documents(kb_dir: Path = KB_DIR) -> list[Document]:
    """Splits each markdown file on '## ' headers into one Document per section,
    attaching source_doc / section metadata for citation (Week 3, Section 2.3)."""
    docs: list[Document] = []
    for md_file in sorted(kb_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        parts = re.split(r"\n(?=## )", content)
        for part in parts:
            part = part.strip()
            if not part or not part.startswith("##"):
                continue
            header_match = re.match(r"##\s+(.+)", part)
            section_title = header_match.group(1).strip() if header_match else "Introduction"
            docs.append(Document(
                page_content=part,
                metadata={"source_doc": md_file.name, "section": section_title},
            ))
    return docs


class KnowledgeRetriever:
    """Wraps two FAISS retrievers (customer-facing, internal-only) behind one class."""

    def __init__(self, kb_dir: Path = KB_DIR):
        all_docs = _load_section_documents(kb_dir)
        public_docs = [d for d in all_docs if d.metadata["source_doc"] != INTERNAL_DOC]
        internal_docs = [d for d in all_docs if d.metadata["source_doc"] == INTERNAL_DOC]

        public_embeddings = LocalTfidfEmbeddings()
        public_embeddings.fit([d.page_content for d in all_docs])  # shared vocabulary
        self._public_store = FAISS.from_documents(public_docs, public_embeddings)

        internal_embeddings = LocalTfidfEmbeddings()
        internal_embeddings.fit([d.page_content for d in all_docs])
        self._internal_store = FAISS.from_documents(internal_docs, internal_embeddings)

        self.public_retriever = self._public_store.as_retriever(search_kwargs={"k": 3})
        self.internal_retriever = self._internal_store.as_retriever(search_kwargs={"k": 2})

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        docs = self.public_retriever.invoke(query)[:top_k]
        return [self._to_chunk(d) for d in docs]

    def retrieve_internal(self, query: str, top_k: int = 2) -> list[dict]:
        docs = self.internal_retriever.invoke(query)[:top_k]
        return [self._to_chunk(d) for d in docs]

    @staticmethod
    def _to_chunk(doc: Document) -> dict:
        return {
            "source_doc": doc.metadata["source_doc"],
            "section": doc.metadata["section"],
            "text": doc.page_content,
        }


if __name__ == "__main__":
    retriever = KnowledgeRetriever()
    for r in retriever.retrieve("customer wants a refund for a damaged item"):
        print(f"  {r['source_doc']} — {r['section']}")
