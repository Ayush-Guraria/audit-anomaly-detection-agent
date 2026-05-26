"""RAG index builder and retriever for audit policy documents."""

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from src.config import get_config

COLLECTION_NAME = "audit_policies"
_CHUNK_SIZE = 1200  # ~300 tokens at ~4 chars/token
_OVERLAP = 200      # ~50 tokens


def _chunk_text(
    text: str, source: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _OVERLAP
) -> list[dict]:
    """Split text into overlapping character-based chunks."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append({"id": f"{source}_{idx}", "text": text[start:end], "source": source})
        idx += 1
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks


def _load_policies(policies_dir: Path) -> list[tuple[str, str]]:
    """Read all .md files from the policies directory, sorted by name."""
    return [
        (f.name, f.read_text(encoding="utf-8"))
        for f in sorted(policies_dir.glob("*.md"))
    ]


def _get_collection(chroma_path: Path, *, create: bool):
    """Return a chromadb collection, optionally dropping and recreating it."""
    ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(chroma_path))
    if create:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        return client.create_collection(COLLECTION_NAME, embedding_function=ef)
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


def build_index() -> None:
    """Build (or rebuild) the chromadb collection from policy documents.

    Idempotent: drops the existing collection before recreating it.
    """
    cfg = get_config()
    chroma_path = cfg.project_root / ".chroma_db"
    chroma_path.mkdir(exist_ok=True)

    collection = _get_collection(chroma_path, create=True)
    policies = _load_policies(cfg.policies_dir)

    all_chunks: list[dict] = []
    for filename, content in policies:
        all_chunks.extend(_chunk_text(content, filename))

    collection.add(
        ids=[c["id"] for c in all_chunks],
        documents=[c["text"] for c in all_chunks],
        metadatas=[{"source": c["source"]} for c in all_chunks],
    )


def retrieve(query: str, k: int = 3) -> list[dict]:
    """Query the policy index and return the top-k chunks.

    Returns a list of dicts with keys ``text`` and ``source``.
    Raises if ``build_index()`` has not been called yet.
    """
    cfg = get_config()
    chroma_path = cfg.project_root / ".chroma_db"
    collection = _get_collection(chroma_path, create=False)
    results = collection.query(query_texts=[query], n_results=k)
    return [
        {"text": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
