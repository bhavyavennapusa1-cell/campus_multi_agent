"""
Memory Module for Smart Campus Multi-Agent System.
Handles student profiles and multi-turn session conversation history.
"""

# Mock student database for quick profile resolution
STUDENT_PROFILES = {
    "1602-22-733-001": {
        "student_id": "1602-22-733-001",
        "name": "Bhavya",
        "year": "3rd Year",
        "branch": "CSE",
        "cgpa": 8.4,
        "attendance_percentage": 72.0,
        "registered_events": ["Hackathon 2026"]
    },
    "default": {
        "student_id": "1602-22-733-099",
        "name": "Sample Student",
        "year": "3rd Year",
        "branch": "CSE",
        "cgpa": 7.8,
        "attendance_percentage": 68.5,
        "registered_events": []
    }
}

# In-memory storage for active sessions
SESSION_MEMORY = {}


def get_student_profile(student_id: str = "default") -> dict:
    """Retrieves student profile attributes."""
    return STUDENT_PROFILES.get(student_id, STUDENT_PROFILES["default"])


def get_session_history(session_id: str) -> list:
    """Returns the conversation history for a given session."""
    return SESSION_MEMORY.get(session_id, [])


def add_to_session_history(session_id: str, role: str, message: str):
    """Appends a new user/agent message to the session history."""
    if session_id not in SESSION_MEMORY:
        SESSION_MEMORY[session_id] = []
    
    SESSION_MEMORY[session_id].append({
        "role": role,
        "content": message
    })


if __name__ == "__main__":
    # Quick sanity check
    profile = get_student_profile("1602-22-733-001")
    print(f"Loaded Profile for {profile['name']}: {profile['branch']} {profile['year']}, CGPA: {profile['cgpa']}")
    
    add_to_session_history("session_1", "user", "Check my exam eligibility")
    print("Session Memory Test:", get_session_history("session_1"))
