import os
import re
import sys
import glob
import json
import logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# pyrefly: ignore [missing-import]
import yaml
from knowledge.memory import log_retrieval

logger = logging.getLogger("rag")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
SYNONYMS_PATH = os.path.join(os.path.dirname(__file__), "synonyms.json")
VALID_CATEGORIES = {"academic", "placement", "campus"}
RETRIEVAL_CONFIDENCE_THRESHOLD = 0.025

_corpus_docs = []
_corpus_metas = []
_corpus_ids = []
_bm25_index = None
_tokenized_corpus = []
_synonyms = {}
collection = None
RAG_READY = False
BM25_READY = False

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "for", "with", "and", "or", "not", "no", "but", "by", "from", "as",
    "this", "that", "these", "those", "it", "its", "what", "which", "who", "whom",
    "how", "when", "where", "why", "can", "could", "would", "should", "do", "does",
    "did", "s", "t", "re", "ve", "m", "ll"
}


def _tokenize(text: str) -> list[str]:
    """Tokenizer with stop-word filtering for BM25."""
    tokens = re.findall(r"\w+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS]


def _load_synonyms():
    """Loads student slang synonym mappings for query expansion."""
    global _synonyms
    if os.path.exists(SYNONYMS_PATH):
        try:
            with open(SYNONYMS_PATH, "r", encoding="utf-8") as f:
                _synonyms = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load synonyms dictionary: {e}")


def _expand_query(query: str) -> str:
    """Expands student query with mapped canonical document keywords."""
    if not _synonyms:
        return query

    query_lower = query.lower()
    tokens = re.findall(r"\w+", query_lower)
    expanded_terms = set()

    for token in tokens:
        if token in _synonyms:
            expanded_terms.add(_synonyms[token])

    if expanded_terms:
        extra_str = " " + " ".join(expanded_terms)
        return query + extra_str
    return query


def _load_lightweight_bm25_corpus():
    """
    Lightweight, fast BM25 corpus loader reading markdown documents directly from disk.
    Requires 0 neural network models, 0 GPU memory, and boots instantly (< 512MB RAM).
    """
    global _corpus_docs, _corpus_metas, _corpus_ids, _tokenized_corpus, _bm25_index, BM25_READY
    try:
        # pyrefly: ignore [missing-import]
        from rank_bm25 import BM25Okapi

        md_files = (
            glob.glob(os.path.join(PROJECT_ROOT, "data", "docs", "**", "*.md"), recursive=True) +
            glob.glob(os.path.join(PROJECT_ROOT, "knowledge", "docs", "**", "*.md"), recursive=True)
        )
        md_files = list(set(md_files))
        md_files = [f for f in md_files if os.path.basename(f).lower() != "readme.md"]

        docs, metas, ids = [], [], []
        for file_path in sorted(md_files):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    yaml_str, body = match.group(1), match.group(2)
                    frontmatter = yaml.safe_load(yaml_str) or {}
                else:
                    frontmatter, body = {}, content

                doc_id = str(frontmatter.get("doc_id", "UNKNOWN"))
                doc_title = str(frontmatter.get("title", "Untitled Document"))
                category = str(frontmatter.get("category", "general")).strip().lower()
                version = str(frontmatter.get("version", "1.0"))
                related_docs = frontmatter.get("related_docs") or []

                # Split body into sections by ## or ### headings
                sections = re.split(r'\n(?=#{1,3}\s+)', body)
                for idx, sec in enumerate(sections):
                    sec_text = sec.strip()
                    if not sec_text:
                        continue
                    sec_lines = sec_text.split("\n")
                    head_match = re.match(r"^#{1,3}\s+(.*)$", sec_lines[0])
                    sec_title = head_match.group(1).strip() if head_match else doc_title

                    cid = f"{doc_id}_{idx}"
                    docs.append(sec_text)
                    metas.append({
                        "doc_id": doc_id,
                        "title": doc_title,
                        "section_title": sec_title,
                        "category": category,
                        "version": version,
                        "related_docs": related_docs
                    })
                    ids.append(cid)
            except Exception:
                continue

        if docs:
            _corpus_docs = docs
            _corpus_metas = metas
            _corpus_ids = ids
            _tokenized_corpus = [_tokenize(doc) for doc in _corpus_docs]
            _bm25_index = BM25Okapi(_tokenized_corpus)
            BM25_READY = True
            print(f"RAG System (Lightweight BM25 Mode): Indexed {len(_corpus_docs)} document chunks.")
    except Exception as e:
        BM25_READY = False
        print(f"Warning: Lightweight BM25 index initialization failed: {e}")


def _init_rag():
    global collection, _corpus_docs, _corpus_metas, _corpus_ids, _tokenized_corpus, _bm25_index, RAG_READY

    _load_synonyms()
    _load_lightweight_bm25_corpus()
    
    # Heavy RAG initialization (SentenceTransformers + ChromaDB vector search)
    try:
        # pyrefly: ignore [missing-import]
        import chromadb
        # pyrefly: ignore [missing-import]
        from chromadb.utils import embedding_functions
        # pyrefly: ignore [missing-import]
        from rank_bm25 import BM25Okapi

        # Auto-ingest if chroma_db directory doesn't exist or collection count is 0
        should_ingest = not os.path.exists(CHROMA_DATA_PATH)
        if not should_ingest:
            try:
                temp_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
                temp_coll = temp_client.get_or_create_collection(name="campus_kb")
                if temp_coll.count() == 0:
                    should_ingest = True
            except Exception:
                should_ingest = True

        if should_ingest:
            print("Auto-triggering RAG document ingestion pipeline for first run...")
            try:
                from knowledge.ingest import ingest_documents
                ingest_documents()
            except Exception as ie:
                print(f"Warning: Auto-ingestion pipeline encountered an error: {ie}")

        print("Initializing RAG Embedding Function and ChromaDB Persistent Client...")
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        collection = chroma_client.get_or_create_collection(
            name="campus_kb",
            embedding_function=embedding_fn
        )

        _corpus_data = collection.get(include=["documents", "metadatas"])
        _corpus_docs = _corpus_data.get("documents") or _corpus_docs
        _corpus_metas = _corpus_data.get("metadatas") or _corpus_metas
        _corpus_ids = _corpus_data.get("ids") or _corpus_ids

        _tokenized_corpus = [_tokenize(doc) for doc in _corpus_docs]
        _bm25_index = BM25Okapi(_tokenized_corpus) if _tokenized_corpus else _bm25_index
        RAG_READY = True
        print(f"RAG System Ready (Full Hybrid Vector + BM25 Mode): Indexed {len(_corpus_docs)} document chunks.")
    except Exception as e:
        RAG_READY = False
        print(f"Warning: Full Heavy RAG initialization deferred/failed gracefully: {e}")


# Initialize RAG on module import
_init_rag()


def format_citation(result: dict) -> str:
    """
    Returns a human-readable citation string like 'Attendance Policy §Condonation Guidelines (v2.1)'.
    """
    if not result:
        return ""
    title_name = result.get("title", "")
    if not title_name:
        doc_id = result.get("doc_id", "Document")
        title_name = doc_id.replace("-", " ").title()
    else:
        title_name = title_name.split("-")[-1].strip() if "-" in title_name else title_name

    sec_title = result.get("section_title", "Overview")
    version = result.get("version", "1.0")

    return f"{title_name} §{sec_title} (v{version})"


def retrieve(query: str, k: int = 3, category: str = None, session_id: str = "global_retrieval", include_related: bool = False) -> list[dict]:
    """
    Retrieves document chunks using Hybrid Vector + BM25 search (if ENABLE_HEAVY_RAG=true)
    or lightweight BM25 keyword search with synonym expansion and passive logging.
    """
    if category is not None:
        category_clean = category.strip().lower()
        if category_clean not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of {sorted(VALID_CATEGORIES)} or None.")
        category = category_clean

    # Query expansion via slang dictionary
    expanded_query = _expand_query(query)

    top_results = []

    # Fallback to BM25-only retrieval when ChromaDB vector index is inactive
    if not RAG_READY or collection is None:
        if BM25_READY and _bm25_index and _corpus_docs:
            try:
                query_tokens = _tokenize(expanded_query)
                bm25_scores = _bm25_index.get_scores(query_tokens)
                sorted_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)

                for idx in sorted_indices:
                    if bm25_scores[idx] <= 0.0:
                        break
                    meta = _corpus_metas[idx]
                    if category and meta.get("category") != category:
                        continue

                    top_results.append({
                        "text": _corpus_docs[idx],
                        "doc_id": meta.get("doc_id", "UNKNOWN"),
                        "title": meta.get("title", ""),
                        "section_title": meta.get("section_title", "Overview"),
                        "category": meta.get("category", ""),
                        "version": meta.get("version", "1.0"),
                        "related_docs": meta.get("related_docs", []),
                        "score": round(bm25_scores[idx], 4)
                    })
                    if len(top_results) >= k:
                        break
            except Exception:
                top_results = []
    else:
        # Full Hybrid ChromaDB + BM25 Retrieval Path
        fetch_k = max(k * 3, 10)
        query_kwargs = {
            "query_texts": [expanded_query],
            "n_results": min(fetch_k, max(len(_corpus_docs), 1))
        }
        if category:
            query_kwargs["where"] = {"category": category}

        try:
            sem_results = collection.query(**query_kwargs)
        except Exception:
            sem_results = None

        sem_ranks = {}
        candidate_map = {}

        if sem_results and sem_results.get("ids") and sem_results["ids"][0]:
            sem_ids = sem_results["ids"][0]
            sem_docs = sem_results["documents"][0]
            sem_metas = sem_results["metadatas"][0]
            for rank, (cid, doc, meta) in enumerate(zip(sem_ids, sem_docs, sem_metas), 1):
                sem_ranks[cid] = rank
                candidate_map[cid] = {"text": doc, "meta": meta}

        bm25_ranks = {}
        if _bm25_index and _tokenized_corpus:
            try:
                query_tokens = _tokenize(expanded_query)
                bm25_scores = _bm25_index.get_scores(query_tokens)
                max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 0.0

                if max_bm25 > 0.0:
                    sorted_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)

                    bm25_rank = 1
                    for idx in sorted_indices:
                        if bm25_scores[idx] <= 0.0:
                            break
                        cid = _corpus_ids[idx]
                        doc = _corpus_docs[idx]
                        meta = _corpus_metas[idx]

                        if category and meta.get("category") != category:
                            continue

                        bm25_ranks[cid] = bm25_rank
                        if cid not in candidate_map:
                            candidate_map[cid] = {"text": doc, "meta": meta}

                        bm25_rank += 1
                        if bm25_rank > fetch_k:
                            break
            except Exception:
                pass

        fused_candidates = []
        for cid, data in candidate_map.items():
            s_rank = sem_ranks.get(cid, 999)
            b_rank = bm25_ranks.get(cid, 999)

            rrf_score = 0.0
            if cid in sem_ranks:
                rrf_score += 1.0 / (60.0 + s_rank)
            if cid in bm25_ranks:
                rrf_score += 1.0 / (60.0 + b_rank)

            meta = data["meta"]
            fused_candidates.append({
                "text": data["text"],
                "doc_id": meta.get("doc_id", "UNKNOWN"),
                "title": meta.get("title", ""),
                "section_title": meta.get("section_title", "Overview"),
                "source_file": meta.get("source_file", ""),
                "category": meta.get("category", ""),
                "version": meta.get("version", "1.0"),
                "related_docs": meta.get("related_docs", []),
                "last_updated": meta.get("last_updated", ""),
                "score": round(rrf_score, 6)
            })

        fused_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_results = fused_candidates[:k]

    if top_results:
        top_score = top_results[0]["score"]
        if top_score < RETRIEVAL_CONFIDENCE_THRESHOLD:
            top_results[0]["low_confidence"] = True

    # Optional: Pull 1 top chunk from each related document if include_related=True
    if include_related and top_results:
        existing_doc_ids = {r["doc_id"] for r in top_results}
        related_to_fetch = set()
        for r in top_results:
            for rel_id in r.get("related_docs", []):
                if rel_id not in existing_doc_ids:
                    related_to_fetch.add(rel_id)

        for rel_id in related_to_fetch:
            for idx, meta in enumerate(_corpus_metas):
                if meta.get("doc_id") == rel_id:
                    top_results.append({
                        "text": _corpus_docs[idx],
                        "doc_id": meta.get("doc_id"),
                        "title": meta.get("title"),
                        "section_title": meta.get("section_title"),
                        "category": meta.get("category"),
                        "version": meta.get("version"),
                        "related_docs": meta.get("related_docs", []),
                        "score": 0.05,
                        "is_related_chunk": True
                    })
                    break

    # Passive Retrieval Logging to SQLite memory.db
    top_ids = [r["doc_id"] for r in top_results]
    top_scores = [r["score"] for r in top_results]
    log_retrieval(session_id=session_id, query=query, top_doc_ids=top_ids, top_scores=top_scores)

    return top_results


if __name__ == "__main__":
    test_res = retrieve("bunking classes and late curfew", k=2, include_related=True)
    for r in test_res:
        print(f"[{r['score']}] {format_citation(r)}: {r['text'][:100]}...")
