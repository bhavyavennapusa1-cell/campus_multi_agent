import os
import httpx
from typing import Dict, Any, List


class JobsAdapter:
    """
    Adapter for Jobs API (e.g. Adzuna, LinkedIn Jobs API, or external job boards).
    Provides live opportunity search with fallback to mock placement data.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("JOBS_API_KEY")

    async def find_opportunities(self, query: str = "Software Engineer", location: str = "Remote") -> Dict[str, Any]:
        if self.api_key:
            try:
                # Example live job search HTTP call
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.adzuna.com/v1/api/jobs/us/search/1",
                        params={"app_id": "hackathon", "app_key": self.api_key, "what": query, "where": location}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results = [
                            {
                                "role": item.get("title"),
                                "company": item.get("company", {}).get("display_name"),
                                "location": item.get("location", {}).get("display_name"),
                                "description": item.get("description")[:150] + "...",
                                "apply_url": item.get("redirect_url")
                            }
                            for item in data.get("results", [])[:5]
                        ]
                        return {"source": "live", "query": query, "opportunities": results}
            except Exception as exc:
                print(f"[JobsAdapter] Live API call failed ({exc}). Falling back to mock response.")

        # Fallback Mock Data
        return {
            "source": "mock",
            "query": query,
            "opportunities": [
                {
                    "company_id": "COMP001",
                    "company_name": "Google",
                    "role": "Software Engineering Intern",
                    "stipend_or_ctc": "$8,000/mo",
                    "min_cgpa": 8.0,
                    "deadline": "2026-08-25"
                },
                {
                    "company_id": "COMP002",
                    "company_name": "Microsoft",
                    "role": "SDE Full Time",
                    "stipend_or_ctc": "18 LPA",
                    "min_cgpa": 7.5,
                    "deadline": "2026-08-28"
                },
                {
                    "company_id": "COMP003",
                    "company_name": "Amazon",
                    "role": "AWS Cloud Specialist",
                    "stipend_or_ctc": "16 LPA",
                    "min_cgpa": 7.0,
                    "deadline": "2026-08-30"
                }
            ]
        }
