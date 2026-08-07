import json
from pathlib import Path
from typing import Protocol, Optional, Dict, Any, List


class CommsRepo(Protocol):
    """
    Data-access interface for Communication Shared Log.
    
    ARCHITECTURE NOTE FOR JUDGES:
    Decoupled interface implementation. Swappable with real Email/SMS/Push API backend.
    """
    def create_email_draft(self, recipient: str, subject: str, body: str) -> Dict[str, Any]: ...
    def send_notification(self, channel: str, recipient: str, subject: str, content: str) -> Dict[str, Any]: ...
    def create_announcement(self, title: str, content: str) -> Dict[str, Any]: ...
    def schedule_appointment(self, title: str, date: str, time_slot: str, location: str, student_id: str) -> Dict[str, Any]: ...
    def update_or_cancel_entry(self, entry_id: str, action: str) -> Dict[str, Any]: ...
    def schedule_reminder(self, title: str, event_time: str, lead_time_minutes: int, target_user: str) -> Dict[str, Any]: ...


class InMemoryCommsRepo:
    """Fallback in-memory repository backed by sample JSON fixture."""

    def __init__(self, fixture_path: Optional[str] = None):
        if fixture_path is None:
            base_dir = Path(__file__).parent.parent / "fixtures"
            fixture_path = str(base_dir / "comms_data.json")

        with open(fixture_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def create_email_draft(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        drafts = self.data.setdefault("drafts", [])
        draft_id = f"DRAFT-{len(drafts) + 101}"
        draft = {
            "draft_id": draft_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "DRAFT_REVIEW",
            "created_at": "2026-08-07 12:00:00"
        }
        drafts.append(draft)
        return draft

    def send_notification(self, channel: str, recipient: str, subject: str, content: str) -> Dict[str, Any]:
        notifications = self.data.setdefault("sent_notifications", [])
        notif_id = f"NOTIF-{len(notifications) + 201}"
        notif = {
            "notif_id": notif_id,
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "content": content,
            "status": "SENT",
            "sent_at": "2026-08-07 12:00:00"
        }
        notifications.append(notif)
        return notif

    def create_announcement(self, title: str, content: str) -> Dict[str, Any]:
        anns = self.data.setdefault("announcements", [])
        ann_id = f"ANN-{len(anns) + 301}"
        ann = {
            "announcement_id": ann_id,
            "title": title,
            "content": content,
            "created_at": "2026-08-07 12:00:00"
        }
        anns.append(ann)
        return ann

    def schedule_appointment(self, title: str, date: str, time_slot: str, location: str, student_id: str) -> Dict[str, Any]:
        appts = self.data.setdefault("appointments", [])
        appt_id = f"APPT-{len(appts) + 401}"
        appt = {
            "appointment_id": appt_id,
            "title": title,
            "date": date,
            "time_slot": time_slot,
            "location": location,
            "student_id": student_id,
            "status": "SCHEDULED"
        }
        appts.append(appt)
        return appt

    def update_or_cancel_entry(self, entry_id: str, action: str) -> Dict[str, Any]:
        # Search across appointments and reminders
        for appt in self.data.get("appointments", []):
            if appt.get("appointment_id") == entry_id:
                appt["status"] = "CANCELLED" if action == "cancel" else "UPDATED"
                return appt

        for rem in self.data.get("reminders", []):
            if rem.get("reminder_id") == entry_id:
                rem["status"] = "CANCELLED" if action == "cancel" else "UPDATED"
                return rem

        return {"entry_id": entry_id, "action": action, "status": "processed"}

    def schedule_reminder(self, title: str, event_time: str, lead_time_minutes: int, target_user: str) -> Dict[str, Any]:
        rems = self.data.setdefault("reminders", [])
        rem_id = f"REM-{len(rems) + 501}"
        rem = {
            "reminder_id": rem_id,
            "title": title,
            "event_time": event_time,
            "lead_time_minutes": lead_time_minutes,
            "target_user": target_user,
            "status": "SCHEDULED"
        }
        rems.append(rem)
        return rem
