import os
import sys

PROJECT_ROOT = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge.rag import retrieve, format_citation

query_text = "placement eligibility Google CGPA"
res = retrieve(query_text, k=2, category="placement")

print("=" * 80)
print(f"BM25 RAG SEARCH TEST (Query: '{query_text}')")
print("=" * 80)
print(f"Total Chunks Retrieved: {len(res)}\n")

for i, r in enumerate(res, 1):
    print(f"[Chunk #{i}] Score: {r['score']} | Citation: {format_citation(r)}")
    print(f"Source File: {r['source_file']}")
    print(f"Doc ID: {r['doc_id']} | Section: {r['section_title']}")
    print("RAW TEXT:")
    print(r["text"])
    print("-" * 60)
