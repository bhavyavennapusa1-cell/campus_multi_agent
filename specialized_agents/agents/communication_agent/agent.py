from typing import Optional, List, Dict, Any
from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.communication_agent.repo import CommsRepo, InMemoryCommsRepo


class CommunicationAgent:
    """
    Communication Agent (Leaf Node)
    
    Owns a shared communication log (emails, notifications, announcements, reminders, appointments).
    Tools: draft_email, send_notification, generate_announcement, schedule_appointment, update_or_cancel_entry, schedule_reminder.
    
    A2A Interactions:
    - THIS AGENT NEVER CALLS OUTWARD. It is a leaf node to avoid call cycles.
    - Mostly called by Academic, Placement, and Campus Agents.
    """

    def __init__(self, registry: AgentRegistry, repo: Optional[CommsRepo] = None):
        self.agent_name = "communication_agent"
        self.registry = registry
        self.repo: CommsRepo = repo or InMemoryCommsRepo()

    async def handle(self, task: TaskRequest) -> ResponseEnvelope:
        tool_name = task.task.lower()
        student_id = task.student_id or task.params.get("student_id") or task.params.get("target_user")

        if tool_name == "draft_email":
            recipient = task.params.get("recipient", "student@campus.edu")
            subject = task.params.get("subject", "Campus Communication")
            body = task.params.get("body", "No content provided.")

            draft = self.repo.create_email_draft(recipient, subject, body)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"draft": draft},
                message=f"Prepared email draft '{draft['draft_id']}' for {recipient} (Status: DRAFT_REVIEW).",
                trace_id=task.trace_id
            )

        elif tool_name == "send_notification":
            channel = task.params.get("channel", "email")
            recipient = task.params.get("recipient") or (f"{student_id}@campus.edu" if student_id else "user@campus.edu")
            subject = task.params.get("subject", "Campus Notification")
            content = task.params.get("content", "No content provided.")

            notif = self.repo.send_notification(channel, recipient, subject, content)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"notification": notif},
                message=f"Dispatched notification '{notif['notif_id']}' via {channel} to {recipient}.",
                trace_id=task.trace_id
            )

        elif tool_name == "generate_announcement":
            title = task.params.get("title", "Campus Announcement")
            content = task.params.get("content", "")

            ann = self.repo.create_announcement(title, content)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"announcement": ann},
                message=f"Created campus announcement '{ann['announcement_id']}'",
                trace_id=task.trace_id
            )

        elif tool_name == "schedule_appointment":
            title = task.params.get("title", "Campus Appointment")
            date = task.params.get("date", "2026-08-08")
            time_slot = task.params.get("time") or task.params.get("time_slot", "14:00-15:00")
            location = task.params.get("location", "Campus Building")

            appt = self.repo.schedule_appointment(title, date, time_slot, location, student_id or "STU_UNKNOWN")
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"appointment": appt},
                message=f"Scheduled calendar appointment '{appt['appointment_id']}' for '{title}' on {date}.",
                trace_id=task.trace_id
            )

        elif tool_name == "update_or_cancel_entry":
            entry_id = task.params.get("entry_id", "UNKNOWN")
            action = task.params.get("action", "cancel")

            res = self.repo.update_or_cancel_entry(entry_id, action)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"result": res},
                message=f"Updated entry '{entry_id}' with action '{action}'.",
                trace_id=task.trace_id
            )

        elif tool_name == "schedule_reminder":
            title = task.params.get("title", "Event Reminder")
            event_time = task.params.get("event_time", "2026-08-08 14:00:00")
            lead_time = int(task.params.get("lead_time_minutes", 60))
            target_user = student_id or task.params.get("target_user", "STU_UNKNOWN")

            rem = self.repo.schedule_reminder(title, event_time, lead_time, target_user)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"reminder": rem},
                message=f"Scheduled reminder '{rem['reminder_id']}' ({lead_time} mins lead time) for user {target_user}.",
                trace_id=task.trace_id
            )

        else:
            return ResponseEnvelope(
                agent=self.agent_name,
                status="error",
                data={"error": f"Unknown tool '{task.task}' for CommunicationAgent"},
                message=f"Tool '{task.task}' is not supported by CommunicationAgent",
                trace_id=task.trace_id
            )
