import os
import glob
import hashlib
import re
import sys
import yaml

# Set project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.check_chunks import semantic_markdown_chunker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    print("STARTING RAG BM25 INGESTION & CHUNKING CHECK")
    print("=" * 80 + "\n")

    # 1. Collect all markdown documents in /data/docs/ and /knowledge/docs/
    md_files = (
        glob.glob(os.path.join(DATA_DOCS_DIR, "**", "*.md"), recursive=True) +
        glob.glob(os.path.join(PROJECT_ROOT, "knowledge", "docs", "**", "*.md"), recursive=True)
    )
    md_files = list(set(md_files))
    md_files = [f for f in md_files if os.path.basename(f).lower() != "readme.md"]

    documents = []
    category_counts = {}

    for file_path in sorted(md_files):
        rel_path = os.path.relpath(file_path, PROJECT_ROOT).replace("\\", "/")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter, body = parse_frontmatter(content)
        category = str(frontmatter.get("category", "general")).strip()

        chunks = semantic_markdown_chunker(body, min_chunk_size=50)

        for chunk_text in chunks:
            documents.append(chunk_text)
            category_counts[category] = category_counts.get(category, 0) + 1

    print(f"Total Chunks Processed: {len(documents)}")
    for cat, count in sorted(category_counts.items()):
        print(f"  - Category '{cat}': {count} chunks")

    print("\n" + "=" * 80)
    print("INGESTION COMPLETE SUMMARY (BM25 Lexical Mode)")
    print("=" * 80)
    print(f"Total Chunks Available for BM25  : {len(documents)}")
    print("Breakdown by Category            :")
    for cat, count in sorted(category_counts.items()):
        print(f"  * {cat:<12} : {count} chunks")
    print("=" * 80)


if __name__ == "__main__":
    ingest_documents()
