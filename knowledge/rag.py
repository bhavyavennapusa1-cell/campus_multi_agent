import os
import re
import sys
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.utils import embedding_functions
# pyrefly: ignore [missing-import]
from rank_bm25 import BM25Okapi

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
VALID_CATEGORIES = {"academic", "placement", "campus"}
RETRIEVAL_CONFIDENCE_THRESHOLD = 0.025

# Module-level initialization of embedding model and ChromaDB client
print("Initializing RAG Embedding Function and ChromaDB Persistent Client...")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(
    name="campus_kb",
    embedding_function=embedding_fn
)

# Load full corpus into memory ONCE at module load time for BM25 indexing
print("Building in-memory BM25 index for hybrid retrieval...")
_corpus_data = collection.get(include=["documents", "metadatas"])
_corpus_docs = _corpus_data.get("documents") or []
_corpus_metas = _corpus_data.get("metadatas") or []
_corpus_ids = _corpus_data.get("ids") or []


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


_tokenized_corpus = [_tokenize(doc) for doc in _corpus_docs]
_bm25_index = BM25Okapi(_tokenized_corpus) if _tokenized_corpus else None
print(f"RAG System Ready: Indexed {len(_corpus_docs)} document chunks.")


def format_citation(result: dict) -> str:
    """
    Returns a human-readable citation string like 'Attendance Policy §2.3 (v2.1)'.
    """
    title_name = result.get("title", "")
    if not title_name:
        doc_id = result.get("doc_id", "Document")
        title_name = doc_id.replace("-", " ").title()
    else:
        title_name = title_name.split("-")[-1].strip() if "-" in title_name else title_name

    sec_title = result.get("section_title", "Overview")
    version = result.get("version", "1.0")

    return f"{title_name} §{sec_title} (v{version})"


def retrieve(query: str, k: int = 3, category: str = None) -> list[dict]:
    """
    Hybrid retrieval using ChromaDB semantic vector search and BM25 keyword search,
    fused via Reciprocal Rank Fusion (RRF).
    """
    if category is not None:
        category_clean = category.strip().lower()
        if category_clean not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of {sorted(VALID_CATEGORIES)} or None.")
        category = category_clean

    # 1. Semantic Search via ChromaDB (fetch top k * 3 candidates)
    fetch_k = max(k * 3, 10)
    query_kwargs = {
        "query_texts": [query],
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

    # 2. BM25 Search
    bm25_ranks = {}
    if _bm25_index and _tokenized_corpus:
        query_tokens = _tokenize(query)
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

                # Filter category if specified
                if category and meta.get("category") != category:
                    continue

                bm25_ranks[cid] = bm25_rank
                if cid not in candidate_map:
                    candidate_map[cid] = {"text": doc, "meta": meta}

                bm25_rank += 1
                if bm25_rank > fetch_k:
                    break

    # 3. Reciprocal Rank Fusion (RRF)
    # RRF score = 1/(60 + sem_rank) + 1/(60 + bm25_rank)
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
            "last_updated": meta.get("last_updated", ""),
            "score": round(rrf_score, 6)
        })

    # Sort descending by fused score
    fused_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_results = fused_candidates[:k]

    # 4. Confidence handling
    if top_results:
        top_score = top_results[0]["score"]
        if top_score < RETRIEVAL_CONFIDENCE_THRESHOLD:
            top_results[0]["low_confidence"] = True

    return top_results


if __name__ == "__main__":
    test_res = retrieve("minimum attendance", k=2)
    for r in test_res:
        print(f"[{r['score']}] {format_citation(r)}: {r['text'][:100]}...")
