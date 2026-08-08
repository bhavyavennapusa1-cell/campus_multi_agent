import os
import re
import sys
import glob
import json
import logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import yaml
from knowledge.memory import log_retrieval

logger = logging.getLogger("rag")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SYNONYMS_PATH = os.path.join(os.path.dirname(__file__), "synonyms.json")
VALID_CATEGORIES = {"academic", "placement", "campus"}
RETRIEVAL_CONFIDENCE_THRESHOLD = 0.025

_corpus_docs = []
_corpus_metas = []
_corpus_ids = []
_bm25_index = None
_tokenized_corpus = []
_synonyms = {}
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
            logger.warning(f"Failed to load synonyms dictionary: {e}")


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
    Fast BM25 corpus loader reading markdown documents directly from disk.
    Requires 0 neural network models, 0 GPU memory, and boots instantly (< 50MB RAM).
    """
    global _corpus_docs, _corpus_metas, _corpus_ids, _tokenized_corpus, _bm25_index, BM25_READY, RAG_READY
    try:
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
                rel_path = os.path.relpath(file_path, PROJECT_ROOT).replace("\\", "/")
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
                        "related_docs": related_docs,
                        "source_file": rel_path
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
            RAG_READY = True
            logger.info(f"RAG System (Lightweight BM25 Mode): Indexed {len(_corpus_docs)} document chunks.")
    except Exception as e:
        BM25_READY = False
        RAG_READY = False
        logger.warning(f"BM25 index initialization failed: {e}")


def _init_rag():
    _load_synonyms()
    _load_lightweight_bm25_corpus()


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


def retrieve(query: str, k: int = 3, category: str = None, session_id: str = "global_retrieval", include_related: bool = False, exclude_malpractice: bool = True) -> list[dict]:
    """
    Retrieves document chunks using lightweight BM25 keyword search with synonym expansion and passive logging.
    By default, exclude_malpractice=True structurally prevents disciplinary punishment policies from being returned for routine queries.
    """
    if category is not None:
        category_clean = category.strip().lower()
        if category_clean not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of {sorted(VALID_CATEGORIES)} or None.")
        category = category_clean

    query_lower = query.lower()
    is_malpractice_query = any(w in query_lower for w in ["malpractice", "cheating", "impersonation", "suspension", "penalty", "punishment", "disciplinary committee"])

    # Query expansion via slang dictionary
    expanded_query = _expand_query(query)
    top_results = []

    if BM25_READY and _bm25_index and _corpus_docs:
        try:
            query_tokens = _tokenize(expanded_query)
            bm25_scores = _bm25_index.get_scores(query_tokens)
            sorted_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)

            for idx in sorted_indices:
                if bm25_scores[idx] <= 0.0:
                    break
                meta = _corpus_metas[idx]
                doc_text = _corpus_docs[idx]

                if category and meta.get("category") != category:
                    continue

                # Anti-Malpractice Guardrail: Never return disciplinary penalties unless explicitly requested
                if exclude_malpractice and not is_malpractice_query:
                    sec_lower = meta.get("section_title", "").lower()
                    if "malpractice" in sec_lower or "category 2 malpractice" in doc_text.lower() or "academic suspension" in doc_text.lower():
                        continue

                top_results.append({
                    "text": doc_text,
                    "doc_id": meta.get("doc_id", "UNKNOWN"),
                    "title": meta.get("title", ""),
                    "section_title": meta.get("section_title", "Overview"),
                    "category": meta.get("category", ""),
                    "version": meta.get("version", "1.0"),
                    "related_docs": meta.get("related_docs", []),
                    "source_file": meta.get("source_file", ""),
                    "score": round(bm25_scores[idx], 4)
                })
                if len(top_results) >= k:
                    break
        except Exception:
            top_results = []

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
                        "source_file": meta.get("source_file", ""),
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
