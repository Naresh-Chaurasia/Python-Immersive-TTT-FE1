import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.v2.engine import PGEngine
from langchain_postgres.v2.async_vectorstore import AsyncPGVectorStore

from .logger import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file (local development).
# Docker deployments set these via env_file in docker-compose.yml.
load_dotenv()

# Read the PostgreSQL connection string from the environment variable.
# Example:
# DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
PG_CONN_STR = os.getenv("DATABASE_URL")
logger.info("DATABASE_URL loaded: %s", "***set***" if PG_CONN_STR else "NOT SET")

# Create a PostgreSQL engine using the connection string.
# This engine manages the database connection and is used by PGVector.
PG_ENGINE = PGEngine.from_connection_string(PG_CONN_STR)
logger.info("PGEngine created successfully")

# Initialize the OpenAI embedding model.
# This model converts text into high-dimensional vectors that can be stored
# and searched using semantic similarity.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
logger.info("OpenAIEmbeddings initialized with model=text-embedding-3-small")


# The `AsyncPGVectorStore` serves as the __vector storage and retrieval layer__ for the RAG pipeline. It:

# - Stores document chunks as vector embeddings in PostgreSQL (using the `pgvector` extension).
# - Enables __semantic similarity search__ — given a query, it finds the most semantically relevant document chunks by comparing vector distances.
# - Supports __metadata filtering__ (by `category`) to narrow down search results.
# - Uses __async operations__ for non-blocking database access, suitable for the FastAPI application.

async def get_vector_store() -> AsyncPGVectorStore:
    """
    Create and return an asynchronous PGVector vector store.

    Configuration:
    - engine: PostgreSQL connection engine.
    - embedding_service: Model used to generate embeddings.
    - table_name: Database table that stores vectors.
    - metadata_json_column: JSON column containing document metadata.
    - metadata_columns: Metadata fields available for filtering searches.
    """
    logger.info("Creating AsyncPGVectorStore (table=%s, metadata_columns=%s)",
                "langchain_pg_embedding", ["category"])
    store = await AsyncPGVectorStore.create(
        # PostgreSQL database engine
        engine=PG_ENGINE,

        # Embedding model used to generate vector representations
        embedding_service=embeddings,

        # Table containing vector embeddings
        table_name="langchain_pg_embedding",

        # JSON column storing metadata for each document
        metadata_json_column="langchain_metadata",

        # Metadata fields that can be used in search filters
        metadata_columns=["category"]
    )
    logger.info("AsyncPGVectorStore created and ready")
    return store
