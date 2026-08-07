"""
Placement Agent for Smart Campus Multi-Agent System.
Evaluates student placement eligibility and internship opportunities using RAG & Memory.
"""

from pathlib import Path
import sys

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session


def check_eligibility(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    company = params.get("company", "Dream Tier").strip()
    company_lower = company.lower()

    # Determine tier category criteria
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

    # Call RAG for authoritative policy context
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
            "policy_summary": top_rag["text"] if top_rag else ""
        },
        message=msg,
        citation=citation
    )


def get_internships(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

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
            ]
        },
        message=f"Found open software engineering internships for {profile['name']} ({profile['branch']}).",
        citation=citation
    )


def general_synthesis(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    query = params.get("query", "placement readiness roadmap tier rules interview prep core dream tier")
    rag_results = retrieve(query, k=2, category="placement")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    context_str = "\n".join([r.get("text", "") for r in rag_results])
    summary = (
        f"Placement Roadmap & Guidance for {profile['name']} (CGPA {profile['cgpa']}, {profile['backlog_count']} backlogs): "
        f"Key requirements & policy context: {context_str[:250]}..."
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "rag_documents": rag_results,
            "synthesis": summary
        },
        message=summary,
        citation=citation
    )


ACTIONS = {
    "check_eligibility": check_eligibility,
    "get_internships": get_internships,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown placement action: {action}")
    return ACTIONS[action](params)

