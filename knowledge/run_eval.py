import os
import sys
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge.rag import retrieve, format_citation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EVAL_PATH = os.path.join(os.path.dirname(__file__), "eval_queries.json")


def run_evaluation():
    if not os.path.exists(EVAL_PATH):
        print(f"Error: Evaluation file '{EVAL_PATH}' not found.")
        sys.exit(1)

    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        eval_queries = json.load(f)

    total_queries = len(eval_queries)
    category_stats = {
        "academic": {"total": 0, "hits": 0},
        "placement": {"total": 0, "hits": 0},
        "campus": {"total": 0, "hits": 0}
    }

    overall_hits = 0
    failing_queries = []

    print("=" * 90)
    print("PRECISION@3 BENCHMARK RETRIEVAL EVALUATION REPORT (40 ODDLY-PHRASED QUERIES)")
    print("=" * 90 + "\n")

    for idx, item in enumerate(eval_queries, 1):
        q_text = item["query"]
        exp_ids = item["expected_doc_id"]
        if isinstance(exp_ids, str):
            expected_set = {exp_ids}
            exp_display = exp_ids
        else:
            expected_set = set(exp_ids)
            exp_display = str(exp_ids)

        exp_cat = item.get("expected_category", "general").lower()
        category_stats[exp_cat]["total"] += 1

        # Run retrieval with category scope
        results = retrieve(q_text, k=3, category=exp_cat, session_id="eval_run")
        returned_ids = [r["doc_id"] for r in results]

        hit = any(eid in returned_ids for eid in expected_set)
        if hit:
            overall_hits += 1
            category_stats[exp_cat]["hits"] += 1
            status = "PASS"
        else:
            status = "FAIL"
            failing_queries.append({
                "idx": idx,
                "query": q_text,
                "category": exp_cat,
                "expected": exp_display,
                "returned": returned_ids,
                "top_citations": [format_citation(r) for r in results]
            })

        print(f"[{idx:02d}/40] [{status}] Cat: {exp_cat:9s} | Expected: {exp_display:20s} | Q: \"{q_text}\"")
        if not hit:
            print(f"       -> FAIL EXPLICIT DETAILS:")
            print(f"          Expected Doc ID: {exp_display}")
            print(f"          Returned Doc IDs: {returned_ids if returned_ids else '[] (No chunks retrieved)'}")
            if results:
                for r_rank, r in enumerate(results, 1):
                    print(f"          Rank {r_rank}: {r['doc_id']} | Score: {r['score']} | {format_citation(r)}")

    print("\n" + "=" * 90)
    print("PRECISION@3 EVALUATION SUMMARY & CATEGORY BREAKDOWN")
    print("=" * 90)

    for cat, stats in category_stats.items():
        tot = stats["total"]
        h = stats["hits"]
        prec = (h / tot * 100.0) if tot > 0 else 0.0
        print(f"Category: {cat.upper():10s} | Queries: {tot:2d} | Hits@3: {h:2d} | Precision@3: {prec:6.2f}%")

    overall_prec = (overall_hits / total_queries * 100.0) if total_queries > 0 else 0.0
    print("-" * 90)
    print(f"OVERALL PRECISION@3 : {overall_hits}/{total_queries} Hits ({overall_prec:.2f}%)")
    print("=" * 90)

    if failing_queries:
        print(f"\nEXPLICIT FAILING QUERIES BREAKDOWN ({len(failing_queries)} FAILS):")
        print("=" * 90)
        for f in failing_queries:
            print(f"Query #{f['idx']} [{f['category']}]: \"{f['query']}\"")
            print(f"  - Expected : {f['expected']}")
            print(f"  - Returned : {f['returned']}")
            print(f"  - Top Cited: {f['top_citations']}\n")
    else:
        print("\nALL 40 EVALUATION QUERIES PASSED WITH 100% PRECISION@3!")


if __name__ == "__main__":
    run_evaluation()
