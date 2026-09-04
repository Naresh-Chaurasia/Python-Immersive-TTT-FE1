from __future__ import annotations
import os, glob, uuid, asyncio, traceback
from typing import Iterable, List, Dict, Any
from pathlib import Path

from langchain_classic.docstore.document import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredMarkdownLoader, PyMuPDFLoader, UnstructuredWordDocumentLoader,TextLoader

from .utils import get_vector_store
from .logger import get_logger
from langchain_postgres.v2.indexes import HNSWIndex, DistanceStrategy

logger = get_logger(__name__)

# Read the data directory from the environment variable.
# If DATA_DIR is not set, default to the "data" folder.
DATA_DIR = os.getenv("DATA_DIR", "data")
logger.info("DATA_DIR = %s", DATA_DIR)

"""
Load supported documents from the specified directory and its subdirectories.

Supported file types:
- Markdown (.md)
- PDF (.pdf)
- Word (.docx)
- Text (.txt)

Each document is tagged with a 'category' based on its parent folder.
"""
def _load_docs(base: str = DATA_DIR) -> List[Document]:

    docs: List[Document] = []
    logger.info("Loading documents from: %s", base)

    # Recursively search for all files inside the base directory.
    for path in glob.glob(os.path.join(base, "**", "*"), recursive=True):

        # Skip directories and hidden files.
        if os.path.isdir(path) or os.path.basename(path).startswith("."):
            continue

        # Extract the file extension.
        ext = os.path.splitext(path)[1].lower()

        # Determine the document category from the first folder name.
        # Example:
        # data/python/file1.pdf  -> category = "python"
        # data/java/file2.md     -> category = "java"
        relative_path = os.path.relpath(path, base)
        category = (
            relative_path.split(os.sep)[0]
            if os.sep in relative_path
            else "general"
        )

        try:
            loaded_docs = []

            # Load Markdown documents.
            if ext == ".md":
                logger.debug("Loading MD: %s (category=%s)", path, category)
                for d in UnstructuredMarkdownLoader(path).load():
                    loaded_docs.append(d)

            # Load PDF documents.
            elif ext == ".pdf":
                logger.debug("Loading PDF: %s (category=%s)", path, category)
                for d in PyMuPDFLoader(path).load():
                    loaded_docs.append(d)

            # Load Microsoft Word documents.
            elif ext == ".docx":
                logger.debug("Loading DOCX: %s (category=%s)", path, category)
                for d in UnstructuredWordDocumentLoader(path).load():
                    loaded_docs.append(d)

            # Load plain text documents.
            elif ext == ".txt":
                logger.debug("Loading TXT: %s (category=%s)", path, category)
                for d in TextLoader(path).load():
                    loaded_docs.append(d)

            # Attach category metadata to every loaded document.
            for d in loaded_docs:
                d.metadata["category"] = category
                docs.append(d)

            if loaded_docs:
                logger.info("Loaded %d document(s) from %s", len(loaded_docs), path)

        except Exception:
            # Continue processing other files even if one fails.
            logger.error("Failed to load %s", path, exc_info=True)

    logger.info("Total documents loaded: %d", len(docs))
    return docs

"""
Split documents into smaller overlapping chunks.

Chunking improves embedding quality and retrieval accuracy.
"""
def _chunk(docs: List[Document]) -> List[Document]:
    logger.info("Starting chunking: %d input document(s)", len(docs))
    splitter = RecursiveCharacterTextSplitter(
        # Maximum characters in each chunk.
        chunk_size=900,

        # Number of overlapping characters between chunks.
        chunk_overlap=120,
    )

    try:
        chunks = splitter.split_documents(docs)
        logger.info("Chunking complete: %d chunks produced", len(chunks))
        return chunks

    except Exception:
        logger.error("Chunking failed", exc_info=True)
        raise

"""
Create an HNSW vector index to speed up similarity searches.

HNSW (Hierarchical Navigable Small World) provides efficient
approximate nearest-neighbor (ANN) search.
"""
async def _create_index(store):
    logger.info("Creating HNSW index (m=16, ef_construction=64, distance=COSINE)")
    index = HNSWIndex(

        # Name of the database index.
        name="hnsw_idx",

        # Use cosine similarity for comparing embeddings.
        distance_strategy=DistanceStrategy.COSINE_DISTANCE,

        # Number of graph connections per node.
        # Higher value improves recall but increases index size.
        m=16,

        # Controls index construction quality.
        # Higher value creates a better index but takes longer.
        ef_construction=64,
    )

    # Create the index asynchronously.
    await store.aapply_vector_index(index, concurrently=True)

    logger.info("HNSW index created successfully")

"""
Complete ingestion pipeline.

Steps:
1. Load documents.
2. Split documents into chunks.
3. Connect to the vector store.
4. Generate embeddings and store them.
5. Create the HNSW vector index.
"""
async def run_ingest_async() -> dict:
    logger.info("=" * 60)
    logger.info("INGESTION PIPELINE STARTED")
    logger.info("=" * 60)

    # Load all supported documents.
    docs = _load_docs()
    logger.info("Step 1/5: Loading documents → %d docs loaded", len(docs))

    # Split documents into chunks.
    chunks = _chunk(docs)
    logger.info("Step 2/5: Chunking → %d chunks produced", len(chunks))

    # Connect to PostgreSQL vector store.
    logger.info("Step 3/5: Connecting to vector store...")
    store = await get_vector_store()
    logger.info("Step 3/5: Vector store connected")

    # Generate embeddings and store them in the database.
    logger.info("Step 4/5: Embedding and storing %d chunks...", len(chunks))
    await store.aadd_documents(chunks)
    logger.info("Step 4/5: Embedding and storage complete")

    logger.info("INGEST: %d documents, %d chunks", len(docs), len(chunks))

    # Build the vector search index.
    logger.info("Step 5/5: Building vector index...")
    await _create_index(store)

    logger.info("=" * 60)
    logger.info("INGESTION PIPELINE COMPLETED")
    logger.info("=" * 60)

    # Return ingestion statistics.
    return {
        "documents": len(docs),
        "chunks": len(chunks),
    }
