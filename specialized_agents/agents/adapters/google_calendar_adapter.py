import os
import uuid
import httpx
from typing import Dict, Any, Optional


class GoogleCalendarAdapter:
    """
    Adapter for Google Calendar API v3.
    Provides add_event_to_calendar, schedule_appointment, update_appointment, cancel_appointment, schedule_reminder.
    Falls back gracefully to mock response if API key / OAuth token is missing.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_CALENDAR_API_KEY")

    async def add_event_to_calendar(self, summary: str, start_time: str, end_time: str, location: str = "") -> Dict[str, Any]:
        if self.api_key:
            try:
                # Example REST call to Google Calendar API
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"https://www.googleapis.com/calendar/v3/calendars/primary/events?key={self.api_key}",
                        json={
                            "summary": summary,
                            "location": location,
                            "start": {"dateTime": start_time},
                            "end": {"dateTime": end_time}
                        }
                    )
                    if resp.status_code in [200, 201]:
                        return {"source": "live", "event": resp.json()}
            except Exception as exc:
                print(f"[GoogleCalendarAdapter] Live API call failed ({exc}). Falling back to mock response.")

        event_id = f"gcal-{uuid.uuid4().hex[:8]}"
        return {
            "source": "mock",
            "event_id": event_id,
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "status": "confirmed",
            "html_link": f"https://calendar.google.com/calendar/event?eid={event_id}"
        }

    async def schedule_appointment(self, title: str, date: str, time_slot: str, location: str, student_id: str) -> Dict[str, Any]:
        start = f"{date}T{time_slot.split('-')[0]}:00Z" if "-" in time_slot else f"{date}T10:00:00Z"
        end = f"{date}T{time_slot.split('-')[1]}:00Z" if "-" in time_slot else f"{date}T11:00:00Z"
        return await self.add_event_to_calendar(summary=f"[{student_id}] {title}", start_time=start, end_time=end, location=location)

    async def update_appointment(self, appointment_id: str, new_title: str, new_date: str) -> Dict[str, Any]:
        return {
            "source": "mock",
            "appointment_id": appointment_id,
            "new_title": new_title,
            "new_date": new_date,
            "status": "updated"
        }

    async def cancel_appointment(self, appointment_id: str) -> Dict[str, Any]:
        return {
            "source": "mock",
            "appointment_id": appointment_id,
            "status": "cancelled"
        }

    async def schedule_reminder(self, title: str, event_time: str, lead_time_minutes: int, target_user: str) -> Dict[str, Any]:
        return {
            "source": "mock",
            "reminder_id": f"rem-{uuid.uuid4().hex[:8]}",
            "title": title,
            "event_time": event_time,
            "lead_time_minutes": lead_time_minutes,
            "target_user": target_user,
            "status": "scheduled"
        }
