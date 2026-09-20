import json
import uuid
from datetime import datetime, timezone

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field
from utils.logger import get_logger
from adapters.hubspot_client import update_hubspot_contact, update_hubspot_deal

# Centralized logger initialize karein
logger = get_logger(__name__)


class SendEmailInput(BaseModel):
    """Validated arguments for sending an operational email."""

    model_config = ConfigDict(extra="forbid")

    to: list[str] = Field(..., min_length=1, description="Recipient email addresses.")
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, description="Complete email body.")
    cc: list[str] = Field(default_factory=list, description="Optional CC recipients.")
    related_contact_id: str | None = Field(
        default=None, description="Optional HubSpot contact ID related to this email."
    )


class ScheduleMeetingInput(BaseModel):
    """Validated arguments for scheduling a calendar meeting."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    start_time: datetime = Field(..., description="ISO-8601 meeting start time.")
    end_time: datetime = Field(..., description="ISO-8601 meeting end time.")
    attendees: list[str] = Field(..., min_length=1, description="Attendee email addresses.")
    timezone_name: str = Field(default="UTC", min_length=1)
    location: str | None = Field(default=None)
    description: str = Field(default="")


class CreateCRMTaskInput(BaseModel):
    """Validated arguments for creating a HubSpot follow-up task."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    due_at: datetime = Field(..., description="ISO-8601 task due date and time.")
    assignee_id: str = Field(..., min_length=1, description="HubSpot owner/user ID.")
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")
    notes: str = Field(default="")
    related_contact_id: str | None = Field(default=None)
    related_deal_id: str | None = Field(default=None)


class ContactUpdateInput(BaseModel):
    """Validated arguments for a CRM record mutation."""

    model_config = ConfigDict(extra="forbid")

    contact_id: str = Field(..., min_length=1)
    update_fields: dict[str, str | None] = Field(..., min_length=1)


class DealUpdateInput(BaseModel):
    """Validated arguments for a HubSpot deal mutation."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., min_length=1)
    update_fields: dict[str, str | None] = Field(..., min_length=1)

@tool(args_schema=ContactUpdateInput)
def update_crm_contact(contact_id: str, update_fields: dict) -> str:
    """
    Use this tool to update ANY information for a contact/candidate in the HubSpot CRM.
    
    Args:
        contact_id: The unique HubSpot ID of the candidate (MANDATORY). You must get this ID from the CRM data.
        update_fields: A dictionary of the fields to update and their new values based on HubSpot property names. 
                       Example: {"phone": "0300-1234567", "lifecyclestage": "customer"}
    """
    logger.info(f"AI Tool Executed: Attempting to update Contact ID '{contact_id}' with fields: {update_fields}")
    
    if not contact_id:
        logger.error("Tool Error: Contact ID was missing or empty.")
        return "ERROR: Contact ID is required to perform an update."

    try:
        # HubSpot API ko PATCH request bhejne wala function call hoga
        success = update_hubspot_contact(contact_id=contact_id, properties=update_fields)
        
        if success:
            logger.info(f"Successfully updated Contact ID '{contact_id}' in HubSpot.")
            return f"SUCCESS: Contact ID '{contact_id}' updated successfully with {update_fields}."
        else:
            logger.error(f"HubSpot API returned failure for Contact ID '{contact_id}'.")
            return f"ERROR: Failed to update Contact ID '{contact_id}' in CRM."
            
    except Exception as e:
        logger.error(f"Exception occurred while executing update_crm_contact tool: {e}")
        return f"ERROR: An exception occurred during CRM update."

@tool(args_schema=DealUpdateInput)
def update_job_deal(job_id: str, update_fields: dict) -> str:
    """
    Use this tool to update ANY information for a job/deal (dealstage, amount, etc.) in the HubSpot CRM.
    
    Args:
        job_id: The unique HubSpot ID of the job/deal (MANDATORY).
        update_fields: A dictionary of the fields to update and their new values.
                       Example: {"dealstage": "appointmentscheduled"}
    """
    logger.info(f"AI Tool Executed: Attempting to update Job/Deal ID '{job_id}' with fields: {update_fields}")
    
    if not job_id:
        logger.error("Tool Error: Job ID was missing or empty.")
        return "ERROR: Job ID is required to perform an update."

    try:
        success = update_hubspot_deal(deal_id=job_id, properties=update_fields)
        if success:
            logger.info("Successfully updated Job ID '%s' in HubSpot.", job_id)
            return f"SUCCESS: Job ID '{job_id}' updated successfully with {update_fields}."
        return f"ERROR: Failed to update Job ID '{job_id}' in CRM."
        
    except Exception as e:
        logger.error(f"Exception occurred while executing update_job_deal tool: {e}")
        return f"ERROR: An exception occurred during Job update."


@tool(args_schema=SendEmailInput)
def send_email(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    related_contact_id: str | None = None,
) -> str:
    """Draft and send a contextual email through the mocked email provider.

    Use this only when the user's request or source email explicitly asks for
    an email to be sent. Do not send a confirmation email merely because a CRM
    update or meeting was completed.
    """
    message_id = f"mock-email-{uuid.uuid4().hex[:12]}"
    payload = {
        "message_id": message_id,
        "status": "sent",
        "to": to,
        "cc": cc or [],
        "subject": subject,
        "body": body,
        "related_contact_id": related_contact_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "provider": "mock",
    }
    logger.info("Email sent via mock provider: message_id=%s recipients=%s", message_id, to)
    return json.dumps(payload)


@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting(
    title: str,
    start_time: datetime,
    end_time: datetime,
    attendees: list[str],
    timezone_name: str = "UTC",
    location: str | None = None,
    description: str = "",
) -> str:
    """Book a meeting through the mocked calendar provider.

    Start and end times must be ISO-8601 values. Use this tool only after the
    requested meeting details are available; never invent an unavailable slot.
    """
    if end_time <= start_time:
        logger.error("Meeting creation rejected: end_time must be after start_time")
        return "ERROR: Meeting end_time must be after start_time."

    event_id = f"mock-event-{uuid.uuid4().hex[:12]}"
    payload = {
        "event_id": event_id,
        "status": "scheduled",
        "title": title,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "timezone": timezone_name,
        "attendees": attendees,
        "location": location,
        "description": description,
        "provider": "mock",
    }
    logger.info("Meeting scheduled via mock provider: event_id=%s", event_id)
    return json.dumps(payload)


@tool(args_schema=CreateCRMTaskInput)
def create_crm_task(
    title: str,
    due_at: datetime,
    assignee_id: str,
    priority: str = "MEDIUM",
    notes: str = "",
    related_contact_id: str | None = None,
    related_deal_id: str | None = None,
) -> str:
    """Create a HubSpot follow-up task through the mocked CRM provider.

    The assignee_id is mandatory. Use related_contact_id or related_deal_id
    whenever the task can be linked to a specific CRM record.
    """
    task_id = f"mock-task-{uuid.uuid4().hex[:12]}"
    payload = {
        "task_id": task_id,
        "status": "created",
        "title": title,
        "due_at": due_at.isoformat(),
        "assignee_id": assignee_id,
        "priority": priority,
        "notes": notes,
        "related_contact_id": related_contact_id,
        "related_deal_id": related_deal_id,
        "provider": "mock",
    }
    logger.info("CRM task created via mock provider: task_id=%s assignee_id=%s", task_id, assignee_id)
    return json.dumps(payload)

# LangGraph ya LLM mein bind karne ke liye tools ki list
crm_tools = [
    update_crm_contact,
    update_job_deal,
    send_email,
    schedule_meeting,
    create_crm_task,
]