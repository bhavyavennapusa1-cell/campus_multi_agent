import os
import glob
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.utils import embedding_functions

# Initialize persistent local DB path
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

# Initialize SentenceTransformer embedding function (Fixes standard Chroma download/hash issue)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Initialize Chroma Client
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(
    name="campus_knowledge",
    embedding_function=embedding_fn
)


def build_index():
    """Reads all markdown files in knowledge/docs/ and indexes them into ChromaDB."""
    md_files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    
    if not md_files:
        print("No markdown documents found in knowledge/docs/")
        return

    documents = []
    metadatas = []
    ids = []

    doc_id = 0
    for file_path in md_files:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Simple section-based chunking by paragraph/heading
        chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
        
        for idx, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"source": filename, "chunk_id": idx})
            ids.append(f"{filename}_{idx}_{doc_id}")
            doc_id += 1

    if documents:
        # Upsert documents into collection
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully indexed {len(documents)} chunks from {len(md_files)} documents.")


def retrieve(query: str, k: int = 3) -> list:
    """
    Searches the knowledge base for relevant chunks.
    Returns a list of dicts with content and source citations.
    """
    results = collection.query(
        query_texts=[query],
        n_results=k
    )

    retrieved_chunks = []
    if results and results.get("documents"):
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        
        for doc, meta in zip(docs, metas):
            retrieved_chunks.append({
                "text": doc,
                "source": meta.get("source", "Unknown Document")
            })

    return retrieved_chunks


if __name__ == "__main__":
    print("Building ChromaDB Index...")
    build_index()
    
    print("\n--- Testing Retrieval ---")
    test_query = "What is the minimum attendance required for exam?"
    results = retrieve(test_query, k=2)
    
    for i, res in enumerate(results, 1):
        print(f"\nResult {i} (Source: {res['source']}):")
        print(f"{res['text']}")
