import os
import httpx
from typing import Dict, Any


class GitHubAdapter:
    """
    Adapter for GitHub REST API.
    Fetches developer profile, repository metrics, contributions, and top skills.
    Falls back gracefully to fixture data if API key is missing or request fails.
    """

    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN")

    async def get_github_profile(self, username: str) -> Dict[str, Any]:
        if not username:
            username = "octocat"

        if self.token:
            try:
                headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github.v3+json"}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"https://api.github.com/users/{username}", headers=headers)
                    if resp.status_code == 200:
                        user_data = resp.json()
                        repos_resp = await client.get(f"https://api.github.com/users/{username}/repos?per_page=10", headers=headers)
                        repos_data = repos_resp.json() if repos_resp.status_code == 200 else []

                        skills = list(set([r.get("language") for r in repos_data if r.get("language")]))
                        return {
                            "source": "live",
                            "username": username,
                            "name": user_data.get("name") or username,
                            "public_repos": user_data.get("public_repos", 0),
                            "followers": user_data.get("followers", 0),
                            "top_skills": skills or ["Python", "JavaScript", "C++"],
                            "profile_url": user_data.get("html_url"),
                            "bio": user_data.get("bio")
                        }
            except Exception as exc:
                print(f"[GitHubAdapter] Live API call failed ({exc}). Falling back to mock response.")

        # Fallback Mock Data
        return {
            "source": "mock",
            "username": username,
            "name": f"{username.capitalize()} (Student Developer)",
            "public_repos": 14,
            "followers": 42,
            "top_skills": ["Python", "Data Structures", "Algorithms", "FastAPI", "React"],
            "profile_url": f"https://github.com/{username}",
            "bio": "CS Major | Open Source Contributor | Full-Stack & AI Enthusiast"
        }
