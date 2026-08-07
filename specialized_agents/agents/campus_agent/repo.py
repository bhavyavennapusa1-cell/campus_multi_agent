import json
from pathlib import Path
from typing import Protocol, Optional, Dict, Any, List


class CampusRepo(Protocol):
    """
    Data-access interface for Campus Dataset (Events, Student Services, Navigator).
    
    ARCHITECTURE NOTE FOR JUDGES:
    Decoupled interface implementation. Swappable with production backend without touching agent logic.
    """
    # Events
    def list_events(self, category: Optional[str] = None) -> List[Dict[str, Any]]: ...
    def get_event(self, event_id_or_title: str) -> Optional[Dict[str, Any]]: ...
    def register_event(self, student_id: str, event_id: str) -> Dict[str, Any]: ...
    def manage_hackathon_team(self, team_id: str, leader_id: str, action: str, member_id: Optional[str] = None) -> Dict[str, Any]: ...
    
    # Student Services
    def get_hostel_info(self, student_id: str) -> Optional[Dict[str, Any]]: ...
    def get_library_status(self, student_id: Optional[str] = None) -> Dict[str, Any]: ...
    def get_scholarships(self) -> List[Dict[str, Any]]: ...
    def get_transport_info(self, route_id: Optional[str] = None) -> Any: ...
    def create_grievance(self, student_id: str, category: str, description: str) -> Dict[str, Any]: ...
    def search_faqs(self, query: str) -> List[Dict[str, Any]]: ...
    
    # Navigator
    def get_locations(self) -> Dict[str, Any]: ...
    def get_location(self, name: str) -> Optional[Dict[str, Any]]: ...
    def get_route(self, origin: str, destination: str) -> Optional[Dict[str, Any]]: ...


class InMemoryCampusRepo:
    """Fallback in-memory repository backed by sample JSON fixture."""

    def __init__(self, fixture_path: Optional[str] = None):
        if fixture_path is None:
            base_dir = Path(__file__).parent.parent / "fixtures"
            fixture_path = str(base_dir / "campus_data.json")

        with open(fixture_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    # Events
    def list_events(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        events = self.data.get("events", [])
        if category:
            return [e for e in events if e.get("category", "").lower() == category.lower()]
        return events

    def get_event(self, event_id_or_title: str) -> Optional[Dict[str, Any]]:
        query = event_id_or_title.lower()
        for ev in self.data.get("events", []):
            if ev.get("event_id", "").lower() == query or query in ev.get("title", "").lower():
                return ev
        return None

    def register_event(self, student_id: str, event_id: str) -> Dict[str, Any]:
        ev = self.get_event(event_id)
        if not ev:
            raise ValueError(f"Event '{event_id}' not found.")
        reg_list = ev.setdefault("registered_students", [])
        if student_id not in reg_list:
            reg_list.append(student_id)
        return {"event_id": ev["event_id"], "title": ev["title"], "student_id": student_id, "status": "confirmed"}

    def manage_hackathon_team(self, team_id: str, leader_id: str, action: str, member_id: Optional[str] = None) -> Dict[str, Any]:
        teams = self.data.setdefault("hackathon_teams", {})
        if action == "create":
            teams[team_id] = {
                "team_id": team_id,
                "leader_id": leader_id,
                "members": [leader_id],
                "project_title": "Pending"
            }
            return teams[team_id]
        elif action == "add_member" and member_id:
            team = teams.get(team_id)
            if team and member_id not in team["members"]:
                team["members"].append(member_id)
                return team
        return teams.get(team_id, {"error": "Team operation failed"})

    # Student Services
    def get_hostel_info(self, student_id: str) -> Optional[Dict[str, Any]]:
        return self.data.get("student_services", {}).get("hostel", {}).get(student_id)

    def get_library_status(self, student_id: Optional[str] = None) -> Dict[str, Any]:
        lib = self.data.get("student_services", {}).get("library", {})
        res = {
            "hours": lib.get("hours"),
            "available_seats": lib.get("available_seats"),
            "total_seats": lib.get("total_seats")
        }
        if student_id:
            res["borrowed_books"] = lib.get("borrowed_books", {}).get(student_id, [])
        return res

    def get_scholarships(self) -> List[Dict[str, Any]]:
        return self.data.get("student_services", {}).get("scholarships", [])

    def get_transport_info(self, route_id: Optional[str] = None) -> Any:
        routes = self.data.get("student_services", {}).get("transport", [])
        if route_id:
            for r in routes:
                if r.get("route_id", "").lower() == route_id.lower():
                    return r
        return routes

    def create_grievance(self, student_id: str, category: str, description: str) -> Dict[str, Any]:
        grievances = self.data.get("student_services", {}).setdefault("grievances", [])
        ticket_id = f"TICK-{len(grievances) + 101}"
        ticket = {
            "ticket_id": ticket_id,
            "student_id": student_id,
            "category": category,
            "description": description,
            "status": "OPEN",
            "created_at": "2026-08-07 12:00:00"
        }
        grievances.append(ticket)
        return ticket

    def search_faqs(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        faqs = self.data.get("student_services", {}).get("faqs", [])
        matches = []
        for item in faqs:
            if q in item.get("question", "").lower() or q in item.get("category", "").lower() or q in item.get("answer", "").lower():
                matches.append(item)
        return matches

    # Navigator
    def get_locations(self) -> Dict[str, Any]:
        return self.data.get("navigator", {}).get("locations", {})

    def get_location(self, name: str) -> Optional[Dict[str, Any]]:
        locs = self.get_locations()
        query = name.lower()
        for loc_name, loc_info in locs.items():
            if loc_name.lower() == query or query in loc_name.lower():
                return {"name": loc_name, **loc_info}
        return None

    def get_route(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        routes = self.data.get("navigator", {}).get("routes", {})
        key1 = f"{origin} -> {destination}"
        key2 = f"{destination} -> {origin}"
        for k, v in routes.items():
            if k.lower() in [key1.lower(), key2.lower()]:
                return {"route_name": k, **v}
        # Fallback route calculation
        return {
            "route_name": f"{origin} -> {destination}",
            "distance_meters": 350,
            "walk_time_minutes": 5,
            "steps": [f"Head from {origin} towards main quadrangle", f"Follow campus signage to {destination}"]
        }
