"""
SupportPilot (LangChain edition) — offline embeddings.

Implements LangChain's `Embeddings` interface backed by scikit-learn's
TF-IDF, so the FAISS vector store in retrieval.py works with zero network
calls and no model downloads. This keeps the capstone runnable in
restricted/offline environments.

Swap this for `OpenAIEmbeddings` or `HuggingFaceEmbeddings` in one line
if you want real semantic embeddings instead of TF-IDF — everything else
(FAISS, the retriever, the chain) stays the same because they only depend
on the `Embeddings` interface, not this implementation.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import TfidfVectorizer


class LocalTfidfEmbeddings(Embeddings):
    """A LangChain-compatible Embeddings implementation with no external calls.

    Must be fit on the full corpus once (via `fit`) before embedding queries,
    so that query vectors and document vectors share the same vocabulary.
    """

    def __init__(self):
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._vectorizer.fit(corpus)
        self._fitted = True

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            self.fit(texts)
        return self._vectorizer.transform(texts).toarray().tolist()

    def embed_query(self, text: str) -> list[float]:
        if not self._fitted:
            raise RuntimeError("LocalTfidfEmbeddings must be fit on a corpus before embedding queries")
        return self._vectorizer.transform([text]).toarray()[0].tolist()
