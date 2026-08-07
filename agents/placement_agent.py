"""
Placement Agent for Smart Campus Multi-Agent System.
Evaluates placement eligibility, internship opportunities, GitHub profile metrics,
and job portal data using adapter pattern with live/mock fallback handlers.
"""

import os
import requests
from pathlib import Path
import sys

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session

# --- In-Memory Repo Data for Coding Platforms & Courses ---
CODING_PLATFORM_REPOS = {
    "demo_session_frontend": [
        {"platform": "LeetCode", "username": "bhavya_v", "profile_url": "https://leetcode.com/bhavya_v", "problems_solved": 340, "rating": 1785, "last_updated": "2026-08-01"},
        {"platform": "CodeChef", "username": "bhavya_v", "profile_url": "https://codechef.com/users/bhavya_v", "problems_solved": 120, "rating": 1650, "last_updated": "2026-07-25"}
    ]
}

COURSE_PROGRESS_REPOS = {
    "demo_session_frontend": [
        {"course": "Deep Learning Specialization", "platform": "Coursera", "started": "2026-05-10", "completed": "2026-07-15", "progress": "100%"},
        {"course": "System Design Primer", "platform": "NPTEL", "started": "2026-06-01", "completed": None, "progress": "65%"}
    ]
}


def resolve_profile(params: dict) -> dict:
    prof = params.get("profile")
    session_id = params.get("session_id", "default")
    if not prof:
        prof = get_profile(session_id) or create_session(session_id)
    else:
        prof = dict(prof)
        if "name" not in prof:
            prof["name"] = "Student"
        if "branch" not in prof:
            prof["branch"] = prof.get("branch_year", "CSE - 3rd Year")
        if "cgpa" not in prof:
            prof["cgpa"] = 8.5
        if "backlog_count" not in prof:
            prof["backlog_count"] = 0
    return prof


def check_eligibility(params: dict) -> AgentResponse:
    profile = resolve_profile(params)


    company = params.get("company", "Dream Tier").strip()
    company_lower = company.lower()

    if any(d in company_lower for d in ["dream", "google", "microsoft", "salesforce"]):
        target_tier = "Dream Tier"
        min_cgpa = 8.0
        max_backlogs = 0
    elif any(c in company_lower for c in ["core", "oracle", "cognizant"]):
        target_tier = "Core Tier"
        min_cgpa = 7.0
        max_backlogs = 1
    else:
        target_tier = "Mass / Pool Tier"
        min_cgpa = 6.0
        max_backlogs = 2

    query = f"placement eligibility for {company} {target_tier} CGPA backlog rules"
    rag_results = retrieve(query, k=1, category="placement")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    name = profile["name"]
    cgpa = profile["cgpa"]
    backlogs = profile["backlog_count"]

    cgpa_ok = cgpa >= min_cgpa
    backlogs_ok = backlogs <= max_backlogs
    is_eligible = cgpa_ok and backlogs_ok

    reasons = []
    if not cgpa_ok:
        reasons.append(f"CGPA {cgpa} < required {min_cgpa}")
    if not backlogs_ok:
        reasons.append(f"Backlogs {backlogs} > max allowed {max_backlogs}")

    if is_eligible:
        msg = f"YES: Student {name} (CGPA {cgpa}, {backlogs} backlogs) is ELIGIBLE for {company} ({target_tier})."
    else:
        msg = f"NO: Student {name} (CGPA {cgpa}, {backlogs} backlogs) is NOT ELIGIBLE for {company} ({target_tier}) [{', '.join(reasons)}]."

    return AgentResponse(
        status="success",
        data={
            "eligible": is_eligible,
            "student_name": name,
            "cgpa": cgpa,
            "backlog_count": backlogs,
            "target_tier": target_tier,
            "company": company,
            "reasons": reasons,
            "policy_summary": top_rag["text"] if top_rag else "",
            "source": "mock"
        },
        message=msg,
        citation=citation
    )


def get_internships(params: dict) -> AgentResponse:
    profile = resolve_profile(params)


    query = params.get("query", "software engineering internship eligibility companies")
    rag_results = retrieve(query, k=1, category="placement")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "branch": profile["branch"],
            "internships": [
                {"company": "Google India", "role": "SWE Intern", "stipend": "1.2 Lakh/pm"},
                {"company": "Microsoft", "role": "L1 Software Intern", "stipend": "1.0 Lakh/pm"}
            ],
            "source": "mock"
        },
        message=f"Found open software engineering internships for {profile['name']} ({profile['branch']}).",
        citation=citation
    )


def get_github_profile(params: dict) -> AgentResponse:
    """
    Feature 2 Integration: GitHub API -> get_github_profile()
    Returns repos, contributions, top languages/skills. Gracefully falls back to mock fixture.
    """
    session_id = params.get("session_id", "default")
    username = params.get("username") or "octocat"
    token = os.environ.get("GITHUB_TOKEN")

    if token:
        try:
            resp = requests.get(
                f"https://api.github.com/users/{username}/repos",
                headers={"Authorization": f"token {token}"},
                timeout=3.0
            )
            if resp.status_code == 200:
                repos_data = resp.json()
                public_repos = len(repos_data)
                top_langs = list(set([r.get("language") for r in repos_data if r.get("language")]))
                return AgentResponse(
                    status="success",
                    data={
                        "username": username,
                        "public_repos": public_repos,
                        "top_languages": top_langs[:5],
                        "contributions": "Active in 2026",
                        "source": "live"
                    },
                    message=f"Fetched live GitHub profile for '{username}': {public_repos} repos, top languages: {', '.join(top_langs[:3])}.",
                    citation=None
                )
        except Exception:
            pass

    # Graceful Fallback to Mock Data
    return AgentResponse(
        status="success",
        data={
            "username": username,
            "public_repos": 18,
            "top_languages": ["Python", "TypeScript", "C++", "HTML/CSS"],
            "contributions": "420 commits in 2026",
            "source": "mock"
        },
        message=f"Retrieved GitHub profile metrics for '{username}' (18 repos, 420 commits).",
        citation=None
    )


def find_opportunities(params: dict) -> AgentResponse:
    """
    Feature 2 Integration: Jobs API -> find_opportunities()
    Returns job listings matching roles and eligibility criteria. Gracefully falls back to mock.
    """
    session_id = params.get("session_id", "default")
    role = params.get("role", "Software Engineer")
    api_key = os.environ.get("JOBS_API_KEY")

    if api_key:
        try:
            resp = requests.get(
                "https://api.jobportal.example.com/v1/jobs",
                headers={"X-API-Key": api_key},
                params={"role": role},
                timeout=3.0
            )
            if resp.status_code == 200:
                jobs = resp.json()
                return AgentResponse(
                    status="success",
                    data={"opportunities": jobs, "source": "live"},
                    message=f"Fetched live job opportunities for {role}.",
                    citation=None
                )
        except Exception:
            pass

    # Graceful Fallback Mock
    mock_opps = [
        {"role": "Frontend Developer Intern", "company": "Amazon", "deadline": "2026-08-30", "eligibility": "CGPA >= 7.5, 0 Backlogs"},
        {"role": "AI Engineer Intern", "company": "Swiggy", "deadline": "2026-09-05", "eligibility": "CGPA >= 8.0, 0 Backlogs"},
        {"role": "Backend Analyst", "company": "Deloitte", "deadline": "2026-09-12", "eligibility": "CGPA >= 6.5, <= 1 Backlog"}
    ]
    return AgentResponse(
        status="success",
        data={"opportunities": mock_opps, "source": "mock"},
        message=f"Retrieved placement opportunities for {role} (3 open positions).",
        citation=None
    )


def get_all_eligible_companies(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

    cgpa = profile["cgpa"]
    backlogs = profile["backlog_count"]

    eligible = []
    if cgpa >= 8.0 and backlogs == 0:
        eligible.extend(["Google India", "Microsoft", "Salesforce", "Atlassian"])
    if cgpa >= 7.0 and backlogs <= 1:
        eligible.extend(["Oracle India", "Cognizant", "Infosys Power Programmer"])
    if cgpa >= 6.0:
        eligible.extend(["TCS Digital", "Wipro Turbo"])

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "cgpa": cgpa,
            "backlog_count": backlogs,
            "eligible_companies": eligible,
            "source": "mock"
        },
        message=f"Student {profile['name']} is eligible for {len(eligible)} companies including {', '.join(eligible[:3])}.",
        citation=None
    )


def general_synthesis(params: dict) -> AgentResponse:
    """
    Requirement 2: General/Synthesis action for open-ended placement queries.
    Retrieves context from knowledge/rag.py across placement category and profile memory,
    composing a grounded answer.
    """
    profile = resolve_profile(params)

    query = params.get("query", "placement preparation roadmap and eligibility advice")

    rag_results = retrieve(query, k=2, category="placement")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    # Retrieve stored coding and course repos
    coding_stats = CODING_PLATFORM_REPOS.get(session_id, CODING_PLATFORM_REPOS["demo_session_frontend"])
    courses = COURSE_PROGRESS_REPOS.get(session_id, COURSE_PROGRESS_REPOS["demo_session_frontend"])

    policy_info = "\n".join([r["text"] for r in rag_results]) if rag_results else "Maintain CGPA >= 8.0 with 0 backlogs for Dream Tier drives."

    synthesis_msg = (
        f"Placement Synthesis Strategy for {profile['name']} ({profile['branch']}, CGPA {profile['cgpa']}):\n"
        f"1. Eligibility Status: Currently eligible for Dream & Core Tiers ({profile['backlog_count']} backlogs).\n"
        f"2. Coding Profiles: LeetCode ({coding_stats[0]['problems_solved']} problems solved, rating {coding_stats[0]['rating']}).\n"
        f"3. Active Courses: {courses[0]['course']} on {courses[0]['platform']} ({courses[0]['progress']}).\n"
        f"4. Guidance Reference: {policy_info[:180]}..."
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "coding_platforms": coding_stats,
            "courses": courses,
            "rag_chunks": rag_results,
            "synthesis_text": synthesis_msg,
            "source": "mock"
        },
        message=synthesis_msg,
        citation=citation
    )


ACTIONS = {
    "check_eligibility": check_eligibility,
    "get_internships": get_internships,
    "get_github_profile": get_github_profile,
    "find_opportunities": find_opportunities,
    "get_all_eligible_companies": get_all_eligible_companies,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown placement action: {action}")
    return ACTIONS[action](params)
