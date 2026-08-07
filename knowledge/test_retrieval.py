import os
import sys

# Set project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge.rag import retrieve, format_citation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_retrieval_tests():
    original_queries = [
        ("What is the minimum attendance percentage required?", None),
        ("What CGPA do I need for a dream company?", None),
        ("What is the hostel curfew time?", None),
        ("How many books can I borrow from the library?", None),
        ("When is the next hackathon?", None)
    ]

    category_queries = [
        ("eligibility rules and CGPA requirements", "placement"),
        ("attendance condonation and medical grounds", "academic")
    ]

    offtopic_queries = [
        ("what's the weather today in Hyderabad", None)
    ]

    total_queries = 0
    passed_queries = 0
    failed_queries = 0
    score_sum = 0.0

    print("=" * 85)
    print("HYBRID RAG RETRIEVAL TEST REPORT")
    print("=" * 85 + "\n")

    # 1. Test original 5 queries
    for q_text, cat in original_queries:
        total_queries += 1
        results = retrieve(q_text, k=3, category=cat)
        top_score = results[0]["score"] if results else 0.0
        score_sum += top_score
        
        passed = len(results) > 0
        if passed:
            passed_queries += 1
        else:
            failed_queries += 1

        print(f"TEST {total_queries} [{ 'PASS' if passed else 'FAIL' }]: \"{q_text}\"")
        print("-" * 85)
        for rank, r in enumerate(results, 1):
            citation = format_citation(r)
            snippet = r["text"].replace("\n", " ")[:100] + "..."
            print(f"  Rank {rank} | Fused Score: {r['score']:.6f} | Citation: {citation}")
            print(f"         Doc ID: {r['doc_id']} | Section: {r['section_title']}")
            print(f"         Snippet: {snippet}")
        print()

    # 2. Test Category Filtering (2 queries)
    for q_text, cat in category_queries:
        total_queries += 1
        results = retrieve(q_text, k=3, category=cat)
        top_score = results[0]["score"] if results else 0.0
        score_sum += top_score

        mismatches = [r for r in results if r["category"] != cat]
        passed = len(results) > 0 and len(mismatches) == 0
        if passed:
            passed_queries += 1
        else:
            failed_queries += 1

        status = "PASS" if passed else "FAIL"
        print(f"TEST {total_queries} [{status}] (Category Filter='{cat}'): \"{q_text}\"")
        print("-" * 85)
        for rank, r in enumerate(results, 1):
            citation = format_citation(r)
            snippet = r["text"].replace("\n", " ")[:100] + "..."
            print(f"  Rank {rank} | Category: {r['category']} | Score: {r['score']:.6f} | Citation: {citation}")
            print(f"         Snippet: {snippet}")
        if mismatches:
            print(f"  - ERROR: Found category mismatches: {[m['category'] for m in mismatches]}")
        print()

    # 3. Test Vague / Off-Topic Query (1 query)
    for q_text, cat in offtopic_queries:
        total_queries += 1
        results = retrieve(q_text, k=3, category=cat)
        top_score = results[0]["score"] if results else 0.0
        score_sum += top_score

        low_conf = results[0].get("low_confidence", False) if results else False
        passed = len(results) > 0 and low_conf is True
        if passed:
            passed_queries += 1
        else:
            failed_queries += 1

        status = "PASS" if passed else "FAIL"
        print(f"TEST {total_queries} [{status}] (Off-Topic Low-Confidence Check): \"{q_text}\"")
        print("-" * 85)
        print(f"  Low Confidence Flag Detected: {low_conf}")
        if results:
            r = results[0]
            print(f"  Top Result Score: {r['score']:.6f} | Citation: {format_citation(r)}")
        print()

    avg_score = round(score_sum / max(total_queries, 1), 6)

    print("=" * 85)
    print("RETRIEVAL TEST SUMMARY")
    print("=" * 85)
    print(f"Total Test Queries Run : {total_queries}")
    print(f"Passed                 : {passed_queries}")
    print(f"Failed                 : {failed_queries}")
    print(f"Average Fused Score    : {avg_score}")
    print("=" * 85)


if __name__ == "__main__":
    run_retrieval_tests()
