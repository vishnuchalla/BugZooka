import os
from typing import Optional

from dotenv import load_dotenv
from llama_index.core import Settings, load_index_from_storage
from llama_index.core.llms.utils import resolve_llm
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

# Fix cache permission issue for non-root containers
os.environ.setdefault("HF_HOME", "/tmp/.cache")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/.cache")
os.environ.setdefault("LLAMA_INDEX_CACHE_DIR", "/tmp/.cache")
os.makedirs("/tmp/.cache", exist_ok=True)


def get_rag_context(query: str, top_k: Optional[int] = None) -> str:
    """Return concatenated top-k chunks from the local FAISS store for a query.

    Reads configuration from environment variables and optional .env files.
    """
    # Load env without overriding already-set variables
    load_dotenv(dotenv_path=".env", override=False)
    load_dotenv(dotenv_path="/app/.env", override=False)

    db_path = os.getenv("RAG_DB_PATH", "/rag")
    index_id = os.getenv("RAG_PRODUCT_INDEX", "vector_db_index")
    embed_model_path = os.getenv(
        "EMBEDDING_MODEL_PATH", "sentence-transformers/all-mpnet-base-v2"
    )
    k = int(os.getenv("RAG_TOP_K", str(top_k if top_k is not None else 5)))

    os.environ.setdefault("TRANSFORMERS_CACHE", embed_model_path)
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")

    Settings.embed_model = HuggingFaceEmbedding(model_name=embed_model_path)
    Settings.llm = resolve_llm(None)

    storage_context = StorageContext.from_defaults(
        vector_store=FaissVectorStore.from_persist_dir(db_path), persist_dir=db_path
    )
    vector_index = load_index_from_storage(
        storage_context=storage_context, index_id=index_id
    )

    retriever = vector_index.as_retriever(similarity_top_k=k)
    nodes = retriever.retrieve(query)

    seen_texts = set()
    formatted_chunks = []
    for i, node in enumerate(nodes, 1):
        text = node.get_text().strip()
        if text not in seen_texts:
            seen_texts.add(text)
            formatted_chunks.append(f"--- Chunk {i} ---\n{text}\n")

    return "\n".join(formatted_chunks)


def main() -> None:
    """CLI entrypoint that mirrors the old rag-client.py behavior."""
    # Load envs and defaults
    load_dotenv(dotenv_path=".env", override=False)
    load_dotenv(dotenv_path="/app/.env", override=False)

    query = os.getenv("RAG_QUERY", "Summarize the the rag database")
    top_k_env = os.getenv("RAG_TOP_K")
    k = int(top_k_env) if top_k_env else None

    # Retrieve chunks and print
    context_text = get_rag_context(query=query, top_k=k)

    print("\n=== Retrieved Chunks ===\n")
    print(context_text)

    # Ask LLM using the same Settings.llm configured in get_rag_context
    prompt = (
        f"Use the following context to answer the question:\n\n{context_text}\n"
        f"Question: {query}"
    )
    answer = Settings.llm.complete(prompt=prompt)

    print("\n=== LLM Answer ===\n")
    print(answer)


if __name__ == "__main__":
    main()
