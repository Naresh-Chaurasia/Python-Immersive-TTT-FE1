from typing import List, Tuple
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.docstore.document import Document

from langchain_core.globals import set_llm_cache

from .utils import get_vector_store
from .logger import get_logger

from langchain_cohere import CohereRerank
from langchain_classic.retrievers import ContextualCompressionRetriever

logger = get_logger(__name__)


# --------------------------------------------------------------------
# System instructions that define the assistant's behaviour.
# These instructions are included in every LLM request.
# --------------------------------------------------------------------
SYSTEM = """You are a helpful company knowledge assistant. Answer the user's question using the provided context.

The context below contains excerpts from company documents. Use the information in the context to answer the user's question.

IMPORTANT: The context contains the information you need. Read it thoroughly. Extract and summarize the relevant details to answer the question. Do NOT say you don't know when the answer is present in the context.
"""


# --------------------------------------------------------------------
# Prompt template passed to the LLM.
#
# The retrieval chain automatically replaces:
#   {input}   -> User's question
#   {context} -> Retrieved document chunks
# --------------------------------------------------------------------
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("user",
     "Question:\n{input}\n\n"
     "Context:\n{context}\n\n"
     "Rule: Prefer the most recent policy by effective date.")
])


# --------------------------------------------------------------------
# Semantic caching has been DISABLED.
#
# RedisSemanticCache matches new questions against previously cached
# questions using embedding similarity. The previous configuration
# (distance_threshold=0.98) was far too permissive, which caused
# completely unrelated questions (e.g. a PTO question vs. a travel
# policy question) to incorrectly return a previously cached,
# unrelated answer.
#
# To avoid returning wrong answers, the semantic cache is disabled
# entirely. Every question is always answered fresh by the LLM.
# --------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")

logger.info(
    "REDIS_URL loaded: %s",
    "***set***" if REDIS_URL else "NOT SET"
)

set_llm_cache(None)

logger.info("Semantic LLM caching disabled (set_llm_cache(None))")


async def _build_chain(category: str = None):
    """
    Build the complete Retrieval-Augmented Generation (RAG) pipeline.

    Pipeline:
        User Question
              ↓
        Vector Retriever
              ↓
        Cohere Reranker
              ↓
        Prompt Template
              ↓
        GPT-4o-mini
              ↓
           Final Answer
    """

    logger.info("Building RAG chain (category=%s)", category)

    # Connect to the PostgreSQL vector store.
    store = await get_vector_store()

    logger.info("Vector store obtained")

    # Number of document chunks to retrieve from the vector database.
    retrieval_k = int(os.getenv("RETRIEVAL_K", "5"))

    search_kwargs = {
        "k": retrieval_k
    }

    # Apply metadata filtering when a category is specified.
    # Example:
    # category="java"
    # Only Java documents will be searched.
    if category:
        search_kwargs["filter"] = {
            "category": category
        }

        logger.info(
            "Search filter applied: category=%s",
            category,
        )

    # Retriever performs vector similarity search.
    base_retriever = store.as_retriever(
        search_kwargs=search_kwargs
    )

    logger.info(
        "Base retriever created (k=%d)",
        retrieval_k,
    )

    # ---------------------------------------------------------
    # Cohere Rerank improves retrieval quality.
    #
    # Vector search retrieves the most similar chunks.
    # The reranker then orders those chunks according to
    # relevance to the user's actual question.
    # ---------------------------------------------------------
    logger.info(
        "Setting up CohereRerank (top_n=3, model=rerank-multilingual-v3.0)"
    )

    compressor = CohereRerank(
        top_n=3,
        model="rerank-multilingual-v3.0",
    )

    # ContextualCompressionRetriever combines
    # vector retrieval with reranking.
    retriever = ContextualCompressionRetriever(
        base_retriever=base_retriever,
        base_compressor=compressor,
    )

    logger.info(
        "ContextualCompressionRetriever with reranker created"
    )

    # Large Language Model used for answer generation.
    llm = ChatOpenAI(
        model="gpt-4o-mini"
    )

    logger.info("LLM initialized: gpt-4o-mini")

    # Stuff chain inserts all retrieved documents into the prompt.
    doc_chain = create_stuff_documents_chain(
        llm,
        PROMPT,
    )

    # Combine retrieval and answer generation into one chain.
    rag_chain = create_retrieval_chain(
        retriever,
        doc_chain,
    )

    logger.info("RAG chain built successfully")

    return rag_chain


async def answer_with_docs_async(
    question: str,
    category: str,
) -> Tuple[str, List[str], List[str]]:
    """
    Execute the complete RAG workflow.

    Steps:
        1. Build the RAG chain.
        2. Retrieve relevant documents.
        3. Generate an answer.
        4. Return answer, source files, and retrieved context.
    """

    logger.info("=" * 60)
    logger.info(
        "RAG QUERY: question='%s', category=%s",
        question,
        category,
    )
    logger.info("=" * 60)

    # Build the retrieval pipeline.
    chain = await _build_chain(category)

    logger.info("Invoking RAG chain...")

    # Execute the complete pipeline. Semantic caching is disabled
    # (see comment above), so every call always hits the LLM fresh.
    result = await chain.ainvoke({
        "input": question
    })

    logger.info("RETRIEVED CONTEXT: %s", result["context"])

    logger.info("RAG chain invocation complete")

    # Generated answer from the LLM.
    answer: str = result["answer"]

    # Retrieved documents used as context.
    docs: List[Document] = result["context"]

    logger.info(
        "Retrieved %d context document(s)",
        len(docs),
    )

    # Collect unique source filenames.
    unique_sources = {
        d.metadata.get("source")
        for d in docs
        if d.metadata.get("source")
    }

    sources = sorted(unique_sources)

    logger.info("Unique sources: %s", sources)

    # Return the retrieved document text.
    # Useful for displaying citations or debugging.
    contexts = []

    for d in docs:
        contexts.append(d.page_content)

    logger.info(
        "Answer (first 200 chars): %s...",
        answer[:200] if answer else "(empty)"
    )

    logger.info("=" * 60)

    return answer, sources, contexts
