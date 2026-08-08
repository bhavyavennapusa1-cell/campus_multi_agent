"""
Unit Test Suite: YouTube Resource Resolution & Accuracy Verification across 8 Diverse Subjects.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.youtube_service import build_search_query, calculate_relevance_score, resolve_youtube_resource
from shared.study_plan_engine import generate_study_plan


class TestYouTubeAccuracy(unittest.TestCase):

    def test_query_builder(self):
        query = build_search_query("Operating Systems", "Process Synchronization & Mutex Semaphores")
        self.assertIn("Operating Systems", query)
        self.assertIn("Process Synchronization", query)
        self.assertIn("lecture", query)

    def test_relevance_score(self):
        # Matching title
        score_match = calculate_relevance_score("Operating Systems", "Process Synchronization", "Process Synchronization & Mutex Semaphores Lecture")
        self.assertGreaterEqual(score_match, 0.2)

        # Mismatched title (ERD diagram for English)
        score_mismatch = calculate_relevance_score("English", "Grammar & Academic Writing", "Entity Relationship Diagram (ERD) Tutorial - Part 1")
        self.assertLess(score_mismatch, 0.2)

    def test_eight_diverse_subjects(self):
        test_subjects = [
            "Operating Systems",
            "English",
            "Discrete Math",
            "Data Structures",
            "Thermodynamics",
            "Organic Chemistry",
            "Microeconomics",
            "Constitutional Law"
        ]

        for subj in test_subjects:
            with self.subTest(subject=subj):
                plan = generate_study_plan(subj, target_deadline=10)
                self.assertEqual(plan["status"], "success")
                subtopics = plan["subtopics"]
                self.assertGreaterEqual(len(subtopics), 1)

                for st in subtopics:
                    for res in st["resources"]:
                        if res["type"] == "video":
                            url = res["url"]
                            title = res["title"]
                            # Must be a live YouTube URL (watch?v= or search results fallback)
                            self.assertTrue(
                                url.startswith("https://www.youtube.com/watch?v=") or
                                url.startswith("https://www.youtube.com/results?search_query="),
                                f"Invalid URL for subject {subj}: {url}"
                            )

                            # Reject mismatched ERD video for English
                            if "English" in subj:
                                self.assertNotIn("Entity Relationship", title)
                                self.assertNotIn("ERD", title)


if __name__ == "__main__":
    unittest.main()
