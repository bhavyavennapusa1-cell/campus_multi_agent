"""
Person C owns this file.
Uses ChromaDB to embed and search the markdown docs in knowledge/docs/.
Run build_index() once at startup (or once ever - it persists to disk).
"""

from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

DOCS_DIR = Path(__file__).resolve().parent / "docs"
DB_DIR = Path(__file__).resolve().parent / "chroma_db"

embedding_fn = embedding_functions.DefaultEmbeddingFunction()

client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_or_create_collection(
    name="campus_knowledge",
    embedding_function=embedding_fn,
)


def build_index():
    """Run this once to load all docs into the vector store. Safe to re-run."""
    existing_ids = set(collection.get()["ids"])

    for doc_path in DOCS_DIR.glob("*.md"):
        text = doc_path.read_text()
        # naive chunking: split on blank lines (paragraphs) - good enough for a hackathon
        chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_path.stem}-{i}"
            if chunk_id in existing_ids:
                continue
            collection.add(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[{"source": doc_path.name}],
            )

    print(f"Index built. {collection.count()} chunks total.")


def retrieve(query: str, k: int = 3) -> list[dict]:
    """
    Returns top-k chunks: [{"text": ..., "source": ...}, ...]
    Agents call this and attach the source filename as the citation
    in their AgentResponse.
    """
    results = collection.query(query_texts=[query], n_results=k)

    if not results["documents"] or not results["documents"][0]:
        return []

    return [
        {"text": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


if __name__ == "__main__":
    build_index()
    # quick manual test
    print(retrieve("what happens if my attendance is low"))
