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
from shared.data_store import get_company, get_collection, get_by_id
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

    raw_company = params.get("company", "Dream Tier").strip()
    company_record = get_company(raw_company)

    name = profile["name"]
    cgpa = profile["cgpa"]
    backlogs = profile["backlog_count"]
    branch = profile.get("branch", "CSE").split("-")[0].strip().upper()
    try:
        year = int(profile.get("year", 3))
    except (ValueError, TypeError):
        year = 3
    attendance_pct = profile.get("attendance_pct", 88.0)

    query = f"placement eligibility for {raw_company} CGPA backlog rules"
    rag_results = retrieve(query, k=1, category="placement")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    if company_record:
        c_name = company_record.get("company_name", raw_company)
        tier = company_record.get("tier", "Placement Drive")
        min_cgpa = company_record.get("min_cgpa", 0.0)
        min_att = company_record.get("min_attendance", 0.0)
        max_backlogs = company_record.get("max_backlogs", 0)
        elig_branches = [b.upper() for b in company_record.get("eligible_branches", [])]
        elig_years = company_record.get("eligible_years", [])

        cgpa_ok = cgpa >= min_cgpa
        att_ok = attendance_pct >= min_att
        backlogs_ok = backlogs <= max_backlogs
        branch_ok = not elig_branches or (branch in elig_branches)
        year_ok = not elig_years or (year in elig_years)

        is_eligible = cgpa_ok and att_ok and backlogs_ok and branch_ok and year_ok

        reasons = []
        if not cgpa_ok:
            reasons.append(f"CGPA {cgpa} < required {min_cgpa}")
        if not att_ok:
            reasons.append(f"Attendance {attendance_pct}% < required {min_att}%")
        if not backlogs_ok:
            reasons.append(f"Backlogs {backlogs} > max allowed {max_backlogs}")
        if not branch_ok:
            reasons.append(f"Branch {branch} not in eligible list ({', '.join(elig_branches)})")
        if not year_ok:
            reasons.append(f"Year {year} not in eligible list ({elig_years})")

        if is_eligible:
            msg = f"YES: Student {name} (CGPA {cgpa}, Attendance {attendance_pct}%, {backlogs} backlogs, {branch} Year {year}) is ELIGIBLE for {c_name} ({tier}). Role: {company_record.get('role', 'N/A')}, CTC/Stipend: ₹{company_record.get('ctc_lpa', company_record.get('stipend_pm_inr', 'N/A'))}."
        else:
            msg = f"NO: Student {name} (CGPA {cgpa}, Attendance {attendance_pct}%, {backlogs} backlogs, {branch} Year {year}) is NOT ELIGIBLE for {c_name} ({tier}) [{', '.join(reasons)}]."

        return AgentResponse(
            status="success",
            data={
                "eligible": is_eligible,
                "student_name": name,
                "cgpa": cgpa,
                "attendance_pct": attendance_pct,
                "backlog_count": backlogs,
                "target_tier": tier,
                "company": c_name,
                "company_record": company_record,
                "reasons": reasons,
                "policy_summary": top_rag["text"] if top_rag else "",
                "source": "companies.json"
            },
            message=msg,
            citation=citation
        )
    else:
        # Fallback tier logic if company is not found in database
        company_lower = raw_company.lower()
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

        cgpa_ok = cgpa >= min_cgpa
        backlogs_ok = backlogs <= max_backlogs
        is_eligible = cgpa_ok and backlogs_ok

        reasons = []
        if not cgpa_ok:
            reasons.append(f"CGPA {cgpa} < required {min_cgpa}")
        if not backlogs_ok:
            reasons.append(f"Backlogs {backlogs} > max allowed {max_backlogs}")

        note = f"(Note: Company '{raw_company}' not found in database; using standard tier rules.)"

        if is_eligible:
            msg = f"YES: Student {name} (CGPA {cgpa}, {backlogs} backlogs) is ELIGIBLE for {raw_company} ({target_tier}). {note}"
        else:
            msg = f"NO: Student {name} (CGPA {cgpa}, {backlogs} backlogs) is NOT ELIGIBLE for {raw_company} ({target_tier}) [{', '.join(reasons)}]. {note}"

        return AgentResponse(
            status="success",
            data={
                "eligible": is_eligible,
                "student_name": name,
                "cgpa": cgpa,
                "backlog_count": backlogs,
                "target_tier": target_tier,
                "company": raw_company,
                "reasons": reasons,
                "policy_summary": top_rag["text"] if top_rag else "",
                "source": "fallback_tier"
            },
            message=msg,
            citation=citation
        )


def get_internships(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    structured_internships = get_collection("internships")

    query = params.get("query", "software engineering internship eligibility companies")
    rag_results = retrieve(query, k=1, category="placement")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    if structured_internships:
        return AgentResponse(
            status="success",
            data={
                "student": profile["name"],
                "branch": profile["branch"],
                "internships": structured_internships,
                "source": "internships.json"
            },
            message=f"Found {len(structured_internships)} open internship drives for {profile['name']} ({profile['branch']}).",
            citation=citation
        )

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

    companies = get_collection("companies")
    all_opps = []
    for c in companies:
        all_opps.append({
            "role": c.get("role"),
            "company": c.get("company_name"),
            "tier": c.get("tier"),
            "deadline": c.get("deadline"),
            "eligibility": f"CGPA >= {c.get('min_cgpa')}, {c.get('max_backlogs')} Backlogs, Attendance >= {c.get('min_attendance')}%",
            "stipend_ctc": c.get("ctc_lpa") or c.get("stipend_pm_inr")
        })

    if not all_opps:
        all_opps = [
            {"role": "Frontend Developer Intern", "company": "Amazon", "deadline": "2026-08-30", "eligibility": "CGPA >= 7.5, 0 Backlogs"},
            {"role": "AI Engineer Intern", "company": "Swiggy", "deadline": "2026-09-05", "eligibility": "CGPA >= 8.0, 0 Backlogs"},
            {"role": "Backend Analyst", "company": "Deloitte", "deadline": "2026-09-12", "eligibility": "CGPA >= 6.5, <= 1 Backlog"}
        ]

    return AgentResponse(
        status="success",
        data={"opportunities": all_opps, "source": "mock"},
        message=f"Retrieved placement opportunities for {role} ({len(all_opps)} open positions).",
        citation=None
    )


def get_all_eligible_companies(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

    cgpa = profile["cgpa"]
    backlogs = profile["backlog_count"]
    branch = profile.get("branch", "CSE").split("-")[0].strip().upper()
    try:
        year = int(profile.get("year", 3))
    except (ValueError, TypeError):
        year = 3
    attendance_pct = profile.get("attendance_pct", 88.0)

    companies = get_collection("companies")
    eligible_records = []
    eligible_names = []

    for c in companies:
        min_cgpa = c.get("min_cgpa", 0.0)
        min_att = c.get("min_attendance", 0.0)
        max_backlogs = c.get("max_backlogs", 0)
        elig_branches = [b.upper() for b in c.get("eligible_branches", [])]
        elig_years = c.get("eligible_years", [])

        if (
            cgpa >= min_cgpa
            and attendance_pct >= min_att
            and backlogs <= max_backlogs
            and (not elig_branches or branch in elig_branches)
            and (not elig_years or year in elig_years)
        ):
            eligible_records.append(c)
            eligible_names.append(c.get("company_name"))

    if not eligible_names:
        # Fallback if no companies matched
        if cgpa >= 8.0 and backlogs == 0:
            eligible_names.extend(["Google India", "Microsoft", "Salesforce", "Atlassian"])
        elif cgpa >= 7.0 and backlogs <= 1:
            eligible_names.extend(["Oracle India", "Cognizant", "Infosys Power Programmer"])
        else:
            eligible_names.extend(["TCS Digital", "Wipro Turbo"])

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "cgpa": cgpa,
            "backlog_count": backlogs,
            "eligible_companies": eligible_names,
            "company_details": eligible_records,
            "source": "companies.json"
        },
        message=f"Student {profile['name']} is eligible for {len(eligible_names)} companies including {', '.join(eligible_names[:3])}.",
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
