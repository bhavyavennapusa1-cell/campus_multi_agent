import os
import glob
import hashlib
import re
import sys
import yaml
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.utils import embedding_functions

# Set project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.check_chunks import semantic_markdown_chunker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
DATA_DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "docs")


def parse_frontmatter(content):
    """Parses YAML frontmatter and body from raw markdown content."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}, content
    yaml_str = match.group(1)
    body = match.group(2)
    try:
        data = yaml.safe_load(yaml_str) or {}
        return data, body
    except Exception:
        return {}, body


def extract_section_title(chunk_text, default_title="Overview"):
    """Extracts nearest ## or ### heading text in chunk."""
    lines = chunk_text.split("\n")
    for line in lines:
        match = re.match(r"^#{1,3}\s+(.*)$", line)
        if match:
            return match.group(1).strip()
    return default_title


def ingest_documents():
    print("=" * 80)
    print("STARTING RAG EMBEDDING AND INGESTION PIPELINE")
    print("=" * 80 + "\n")

    # 1. Collect all markdown documents in /data/docs/
    md_files = glob.glob(os.path.join(DATA_DOCS_DIR, "**", "*.md"), recursive=True)
    md_files = [f for f in md_files if os.path.basename(f).lower() != "readme.md"]

    documents = []
    metadatas = []
    ids = []
    category_counts = {}

    for file_path in sorted(md_files):
        rel_path = os.path.relpath(file_path, PROJECT_ROOT).replace("\\", "/")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter, body = parse_frontmatter(content)
        doc_id = str(frontmatter.get("doc_id", "UNKNOWN"))
        doc_title = str(frontmatter.get("title", "Untitled Document"))
        category = str(frontmatter.get("category", "general")).strip()
        version = str(frontmatter.get("version", "1.0"))
        effective_date = str(frontmatter.get("effective_date", ""))
        last_updated = str(frontmatter.get("last_updated", ""))

        # Chunk using imported semantic_markdown_chunker
        chunks = semantic_markdown_chunker(body, min_chunk_size=50)

        for idx, chunk_text in enumerate(chunks):
            sec_title = extract_section_title(chunk_text, default_title=doc_title)
            
            # Deterministic, unique chunk_id hash
            unique_str = f"{doc_id}_{sec_title}_{idx}"
            chunk_hash = hashlib.md5(unique_str.encode("utf-8")).hexdigest()[:10]
            chunk_id = f"{doc_id}_{idx}_{chunk_hash}"

            metadata = {
                "doc_id": doc_id,
                "title": doc_title,
                "category": category,
                "version": version,
                "effective_date": effective_date,
                "last_updated": last_updated,
                "section_title": sec_title,
                "source_file": rel_path
            }

            documents.append(chunk_text)
            metadatas.append(metadata)
            ids.append(chunk_id)

            category_counts[category] = category_counts.get(category, 0) + 1

    print(f"Total Chunks Prepared: {len(documents)}")
    for cat, count in sorted(category_counts.items()):
        print(f"  - Category '{cat}': {count} chunks")

    # 2. Initialize SentenceTransformer & ChromaDB
    print("\nInitializing SentenceTransformer ('all-MiniLM-L6-v2')...")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    collection = chroma_client.get_or_create_collection(
        name="campus_kb",
        embedding_function=embedding_fn
    )

    print("Upserting chunks into ChromaDB collection 'campus_kb'...")
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    total_in_db = collection.count()
    print("\n" + "=" * 80)
    print("INGESTION COMPLETE SUMMARY")
    print("=" * 80)
    print(f"Total Chunks Embedded & Upserted : {len(documents)}")
    print("Breakdown by Category            :")
    for cat, count in sorted(category_counts.items()):
        print(f"  * {cat:<12} : {count} chunks")
    print(f"Total Collection Count in DB     : {total_in_db}")
    print("=" * 80)


if __name__ == "__main__":
    ingest_documents()
