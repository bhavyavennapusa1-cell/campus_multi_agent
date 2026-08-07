import uuid
from typing import Optional, List, Dict, Any

from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.communication_agent.repo import CommsRepo, InMemoryCommsRepo
from agents.communication_agent.contacts_repo import ContactsRepo, InMemoryContactsRepo
from agents.communication_agent.db import create_group, get_active_groups
from agents.adapters.gmail_adapter import GmailAdapter
from agents.adapters.google_calendar_adapter import GoogleCalendarAdapter

# Global store for human-in-the-loop pending approval actions
PENDING_APPROVAL_ACTIONS: Dict[str, Dict[str, Any]] = {}


class CommunicationAgent:
    """
    Communication Agent (Leaf Node)
    
    Owns shared communication log, contacts read interface, and local SQLite chat group operational state.
    Tools:
    - Base: draft_email, send_notification, generate_announcement, schedule_appointment, update_or_cancel_entry, schedule_reminder
    - Expanded: get_relevant_contacts, create_chat_group, draft_official_email
    
    A2A Interactions:
    - THIS AGENT NEVER CALLS OUTWARD. It is a leaf node to avoid call cycles.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        repo: Optional[CommsRepo] = None,
        contacts_repo: Optional[ContactsRepo] = None,
        gmail_adapter: Optional[GmailAdapter] = None,
        calendar_adapter: Optional[GoogleCalendarAdapter] = None
    ):
        self.agent_name = "communication_agent"
        self.registry = registry
        self.repo: CommsRepo = repo or InMemoryCommsRepo()
        self.contacts_repo: ContactsRepo = contacts_repo or InMemoryContactsRepo()
        self.gmail_adapter = gmail_adapter or GmailAdapter()
        self.calendar_adapter = calendar_adapter or GoogleCalendarAdapter()

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

        elif tool_name == "draft_official_email":
            recipient = task.params.get("recipient_email") or task.params.get("recipient", "dean@campus.edu")
            subject = task.params.get("subject", "Official Campus Inquiry")
            core_message = task.params.get("core_message") or task.params.get("body", "")

            action_id = f"act-{uuid.uuid4().hex[:8]}"
            formatted_body = (
                f"Respected Sir/Madam,\n\n"
                f"{core_message}\n\n"
                f"Student ID: {student_id or 'STU001'}\n"
                f"Smart Campus Portal Automated Draft"
            )

            action_record = {
                "action_id": action_id,
                "type": "send_email",
                "recipient_email": recipient,
                "subject": subject,
                "body": formatted_body,
                "student_id": student_id,
                "status": "pending_user_approval"
            }
            PENDING_APPROVAL_ACTIONS[action_id] = action_record

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={
                    "action_id": action_id,
                    "to": recipient,
                    "subject": subject,
                    "body": formatted_body,
                    "requires_user_approval": True
                },
                message=f"Official email drafted for '{recipient}'. Requires human approval (action_id: {action_id}).",
                trace_id=task.trace_id
            )

        elif tool_name == "get_relevant_contacts":
            query_type = task.params.get("query_type", "faculty")
            subject = task.params.get("subject")
            contacts = self.contacts_repo.get_by_query(student_id or "STU001", query_type, subject)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"query_type": query_type, "contacts": contacts},
                message=f"Found {len(contacts)} relevant contacts for query '{query_type}'",
                trace_id=task.trace_id
            )

        elif tool_name == "create_chat_group":
            group_name = task.params.get("group_name", "Campus Study Group")
            member_ids = task.params.get("member_ids", ["STU001", "STU002"])
            group_type = task.params.get("group_type", "temporary")
            duration_hours = int(task.params.get("duration_hours", 24)) if task.params.get("duration_hours") else None
            group_id = f"GRP-{uuid.uuid4().hex[:6]}"

            res = create_group(group_id, group_name, member_ids, group_type, student_id or "STU001", duration_hours)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"group": res},
                message=f"Created {group_type} chat group '{group_name}' ({len(member_ids)} members).",
                trace_id=task.trace_id
            )

        elif tool_name == "get_active_groups":
            groups = get_active_groups()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"groups": groups},
                message=f"Retrieved {len(groups)} active chat groups",
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

            gcal_res = await self.calendar_adapter.schedule_appointment(title, date, time_slot, location, student_id or "STU001")
            appt = self.repo.schedule_appointment(title, date, time_slot, location, student_id or "STU_UNKNOWN")
            
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"appointment": appt, "gcal_sync": gcal_res, "source": gcal_res.get("source", "mock")},
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

            gcal_rem = await self.calendar_adapter.schedule_reminder(title, event_time, lead_time, target_user)
            rem = self.repo.schedule_reminder(title, event_time, lead_time, target_user)
            
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"reminder": rem, "gcal_sync": gcal_rem, "source": gcal_rem.get("source", "mock")},
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
