"""
Campus Navigator Agent for Smart Campus Multi-Agent System.
Handles on-campus and off-campus directions using campus DB and Google Maps API fallback.
"""

import os
import requests
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session

ON_CAMPUS_LOCATIONS = {
    "library": "Central Library Building, 2nd Floor",
    "cse dept": "Tech Block A, Floor 3, Room 302",
    "canteen": "Student Activity Center Ground Floor",
    "auditorium": "Main Administrative Block Auditorium",
    "hostel b": "Hostel Block B, East Wing",
}


CAMPUS_COORDINATES = {
    "library": (17.4458, 78.3482, "Central Library & Knowledge Center"),
    "central library": (17.4458, 78.3482, "Central Library & Knowledge Center"),
    "cse": (17.4465, 78.3495, "Computer Science Dept & AI Lab"),
    "computer science": (17.4465, 78.3495, "Computer Science Dept & AI Lab"),
    "canteen": (17.4450, 78.3505, "Student Activity & Food Court"),
    "hostel": (17.4440, 78.3470, "Boys Hostel Block B"),
    "hostel b": (17.4440, 78.3470, "Boys Hostel Block B"),
    "hostel a": (17.4435, 78.3460, "Girls Hostel Block A"),
    "auditorium": (17.4452, 78.3478, "Main Auditorium"),
    "sports": (17.4472, 78.3465, "Sports Complex"),
}


def resolve_location_coords(destination: str):
    dest_lower = destination.lower()
    for key, (lat, lng, name) in CAMPUS_COORDINATES.items():
        if key in dest_lower:
            return lat, lng, name
    return 17.4458, 78.3482, destination


def get_directions(params: dict) -> AgentResponse:
    origin = params.get("origin", "Hostel Block B")
    destination = params.get("destination", "Central Library")
    lat, lng, loc_name = resolve_location_coords(destination)
    google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    actions = [{"type": "link", "label": "Get Directions", "url": google_maps_url}]

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

    # Check on-campus dictionary/RAG first (Bhavya's dataset priority)
    dest_lower = destination.lower()
    on_campus_match = None
    for loc_key, loc_desc in ON_CAMPUS_LOCATIONS.items():
        if loc_key in dest_lower:
            on_campus_match = loc_desc
            break

    if on_campus_match:
        return AgentResponse(
            status="success",
            data={
                "origin": origin,
                "destination": destination,
                "directions": f"Walk straight from {origin} past SAC circle to {on_campus_match}.",
                "google_maps_url": google_maps_url,
                "actions": actions,
                "source": "mock"
            },
            message=f"Directions to {destination}: {on_campus_match} (via campus internal routing).",
            citation=None,
            actions=actions
        )

    # Off-campus fallback via Google Maps API
    if api_key:
        try:
            resp = requests.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={"origin": origin, "destination": destination, "key": api_key},
                timeout=3.0
            )
            if resp.status_code == 200 and resp.json().get("status") == "OK":
                routes = resp.json().get("routes", [])
                leg = routes[0]["legs"][0]
                return AgentResponse(
                    status="success",
                    data={
                        "origin": origin,
                        "destination": destination,
                        "distance": leg["distance"]["text"],
                        "duration": leg["duration"]["text"],
                        "steps": [s["html_instructions"] for s in leg["steps"][:3]],
                        "google_maps_url": google_maps_url,
                        "actions": actions,
                        "source": "live"
                    },
                    message=f"Google Maps directions from {origin} to {destination} ({leg['distance']['text']}, {leg['duration']['text']}).",
                    citation=None,
                    actions=actions
                )
        except Exception:
            pass

    # Graceful Fallback
    return AgentResponse(
        status="success",
        data={
            "origin": origin,
            "destination": destination,
            "distance": "1.8 km",
            "duration": "6 mins drive",
            "google_maps_url": google_maps_url,
            "actions": actions,
            "source": "mock"
        },
        message=f"Directions from {origin} to {destination}: Take Main Gate Road -> Outer Ring Road exit.",
        citation=None,
        actions=actions
    )



def find_nearby_facilities(params: dict) -> AgentResponse:
    facility_type = params.get("facility_type", "ATM / Printing Shop")
    return AgentResponse(
        status="success",
        data={
            "facility_type": facility_type,
            "facilities": [
                {"name": "SBI Campus ATM", "location": "Near Gate 1", "distance": "200m"},
                {"name": "Xerox & Stationery Store", "location": "SAC Complex", "distance": "150m"}
            ],
            "source": "mock"
        },
        message=f"Found nearby {facility_type} facilities on campus.",
        citation=None
    )


def resolve_profile(params: dict) -> dict:
    prof = params.get("profile")
    session_id = params.get("session_id", "default")
    if not prof:
        prof = get_profile(session_id) or create_session(session_id)
    else:
        prof = dict(prof)
        if "name" not in prof:
            prof["name"] = "Student"
    return prof


def general_synthesis(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    query = params.get("query", "campus navigation building locations facilities")


    rag_results = retrieve(query, k=2, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    synthesis_msg = (
        f"Campus Navigator Overview for {profile['name']}:\n"
        f"1. Core Landmarks: Tech Block A (CSE), Central Library (Block B), SAC Canteen.\n"
        f"2. Navigation Guidance: On-campus locations use internal walking routes. Off-campus locations route via Google Maps.\n"
        f"3. Facility Note: {top_rag['text'][:150] if top_rag else 'Campus map available at Main Gate entrance.'}"
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "rag_chunks": rag_results,
            "synthesis_text": synthesis_msg,
            "source": "mock"
        },
        message=synthesis_msg,
        citation=citation
    )


ACTIONS = {
    "get_directions": get_directions,
    "find_nearby_facilities": find_nearby_facilities,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown navigator action: {action}")
    return ACTIONS[action](params)
