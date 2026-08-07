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
    varied_queries = [
        # Academic Domain Queries
        ("What is the minimum attendance percentage required?", "academic"),
        ("Can I write SEE exams if I was hospitalized and had 68% attendance?", "academic"),
        ("What are the minimum passing marks in internal assessment versus end sem?", "academic"),
        ("How many backlogs can I have before I am blocked from entering 4th year?", "academic"),
        ("Where is the CSE department HOD office located?", "academic"),

        # Placement Domain Queries
        ("What CGPA do I need for a dream company?", "placement"),
        ("If I get a job offer from TCS, can I still sit for Microsoft placement drives?", "placement"),
        ("What happens if I register for Google placement online test but don't show up?", "placement"),
        ("Can 3rd year ECE students apply for Salesforce software engineering role?", "placement"),

        # Campus & Student Services Queries
        ("What is the hostel curfew time?", "campus"),
        ("What is the penalty if I return to hostel Block-A after 11:30 PM on weekend?", "campus"),
        ("How many books can I borrow from the library?", "campus"),
        ("How do I apply for post-matric tuition fee reimbursement scholarship?", "campus"),
        ("Who is the coordinator to contact if my hostel room plumbing ticket is not resolved in 2 days?", "campus"),
        ("Where do campus buses from Kukatpally stop?", "campus"),
        ("When is the next hackathon?", "campus"),

        # Off-Topic / Unmatched Query
        ("What is the formula for calculating quantum entanglement in black holes?", None)
    ]

    total_queries = 0
    passed_queries = 0
    failed_queries = 0
    score_sum = 0.0

    print("=" * 85)
    print("RELEVANCE & GROUNDING RAG RETRIEVAL SUITE")
    print("=" * 85 + "\n")

    for q_text, cat in varied_queries:
        total_queries += 1
        results = retrieve(q_text, k=2, category=cat)
        top_score = results[0]["score"] if results else 0.0
        score_sum += top_score
        
        passed = len(results) > 0
        if passed:
            passed_queries += 1
        else:
            failed_queries += 1

        status_str = "PASS" if passed else "FAIL"
        cat_str = f" [Category: {cat}]" if cat else ""
        print(f"TEST {total_queries:02d} [{status_str}]{cat_str}: \"{q_text}\"")
        print("-" * 85)
        if results:
            for rank, r in enumerate(results, 1):
                citation = format_citation(r)
                snippet = r["text"].replace("\n", " ")[:110] + "..."
                print(f"  Rank {rank} | Score: {r['score']:.4f} | Citation: {citation}")
                print(f"         Snippet: {snippet}")
        else:
            print("  - WARNING: No relevant document chunks retrieved (Corpus Gap Detected).")
        print()

    avg_score = round(score_sum / max(total_queries, 1), 4)

    print("=" * 85)
    print("RETRIEVAL SUITE TEST SUMMARY")
    print("=" * 85)
    print(f"Total Queries Evaluated : {total_queries}")
    print(f"Passed Retrieval       : {passed_queries}")
    print(f"Failed / Gap Detected   : {failed_queries}")
    print(f"Average BM25 Score     : {avg_score}")
    print("=" * 85)


if __name__ == "__main__":
    run_retrieval_tests()
