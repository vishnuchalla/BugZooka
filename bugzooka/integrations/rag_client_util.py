import logging
import os
import threading
from typing import Optional

from dotenv import load_dotenv

from bugzooka.core.constants import RAG_TOP_K_DEFAULT
from llama_index.core import Settings, load_index_from_storage
from llama_index.core.llms.utils import resolve_llm
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

logger = logging.getLogger(__name__)

# Fix cache permission issue for non-root containers
os.environ.setdefault("HF_HOME", "/tmp/.cache")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/.cache")
os.environ.setdefault("LLAMA_INDEX_CACHE_DIR", "/tmp/.cache")
os.makedirs("/tmp/.cache", exist_ok=True)

# Thread-safe singleton for RAG resources
_rag_lock = threading.Lock()
_rag_initialized = False
_vector_index = None


def _initialize_rag():
    """Initialize RAG resources once (called with lock held)."""
    global _rag_initialized, _vector_index

    if _rag_initialized:
        return

    # Load env without overriding already-set variables
    load_dotenv(dotenv_path=".env", override=False)
    load_dotenv(dotenv_path="/app/.env", override=False)

    db_path = os.getenv("RAG_DB_PATH", "/rag")
    index_id = os.getenv("RAG_PRODUCT_INDEX", "vector_db_index")
    embed_model_path = os.getenv(
        "EMBEDDING_MODEL_PATH", "sentence-transformers/all-mpnet-base-v2"
    )

    os.environ.setdefault("TRANSFORMERS_CACHE", embed_model_path)
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")

    logger.info(
        "Initializing RAG: db_path=%s, index_id=%s, embed_model=%s",
        db_path,
        index_id,
        embed_model_path,
    )

    # Set global LlamaIndex settings (only once)
    Settings.embed_model = HuggingFaceEmbedding(model_name=embed_model_path)
    Settings.llm = resolve_llm(None)

    # Load vector store and index (only once)
    storage_context = StorageContext.from_defaults(
        vector_store=FaissVectorStore.from_persist_dir(db_path), persist_dir=db_path
    )
    _vector_index = load_index_from_storage(
        storage_context=storage_context, index_id=index_id
    )

    _rag_initialized = True
    logger.info("RAG initialization complete")


def get_rag_context(query: str, top_k: Optional[int] = None) -> str:
    """Return concatenated top-k chunks from the local FAISS store for a query.

    Thread-safe: initializes RAG resources once, creates retriever per query
    to allow concurrent retrievals without locking.
    """
    k = int(
        os.getenv("RAG_TOP_K", str(top_k if top_k is not None else RAG_TOP_K_DEFAULT))
    )

    # Thread-safe initialization (lock only held during init)
    with _rag_lock:
        if not _rag_initialized:
            _initialize_rag()
        # Create a new retriever for this query (allows concurrent retrievals)
        assert _vector_index is not None, "RAG index failed to initialize"
        retriever = _vector_index.as_retriever(similarity_top_k=k)

    # Retrieval happens outside the lock for better concurrency
    nodes = retriever.retrieve(query)

    seen_texts = set()
    formatted_chunks = []
    for i, node in enumerate(nodes, 1):
        text = node.get_text().strip()
        if text not in seen_texts:
            seen_texts.add(text)
            formatted_chunks.append(f"--- Chunk {i} ---\n{text}\n")

    return "\n".join(formatted_chunks)
