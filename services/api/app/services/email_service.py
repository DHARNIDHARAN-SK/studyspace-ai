from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
from typing import Any, Dict, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger

TARGET_NOTIFICATION_EMAIL = "karnan284858@gmail.com"


class ContactInquiryPayload(BaseModel):
    name: str
    email: str
    institution: Optional[str] = None
    message: str


class DeveloperAccessRequestPayload(BaseModel):
    name: str
    organization: str
    email: str
    phone: Optional[str] = None
    intended_use: str
    help_needed: str
    heard_about: str
    additional_message: Optional[str] = None


class EmailDeliveryResult(BaseModel):
    success: bool
    status: str  # "delivered" | "queued_manual_setup_required" | "failed"
    message: str
    timestamp: str


def _send_smtp_email(subject: str, text_content: str, to_email: str = TARGET_NOTIFICATION_EMAIL) -> EmailDeliveryResult:
    """
    Dispatches a real email via server-side SMTP credentials configured in environment variables.
    Does NOT expose credentials to the client or source control.
    If SMTP credentials are not configured, records the message and returns the exact manual setup required.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("SMTP_FROM_EMAIL", smtp_user or "notifications@studyspace.ai")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Verify if SMTP provider credentials are fully configured
    if not smtp_host or not smtp_pass:
        msg = (
            f"SMTP credentials not configured in server environment. "
            f"To enable direct delivery to {to_email}, configure SMTP_HOST, SMTP_PORT, "
            f"SMTP_USERNAME, and SMTP_PASSWORD in .env."
        )
        logger.warning(
            "Email notification recorded for %s, but SMTP is unconfigured. Content preview: %s",
            to_email,
            subject,
        )
        return EmailDeliveryResult(
            success=True,
            status="queued_manual_setup_required",
            message=msg,
            timestamp=now_iso,
        )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.attach(MIMEText(text_content, "plain"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())

        logger.info("Successfully delivered email '%s' to %s", subject, to_email)
        return EmailDeliveryResult(
            success=True,
            status="delivered",
            message=f"Email successfully delivered to {to_email}",
            timestamp=now_iso,
        )
    except Exception as exc:
        logger.error("Failed to send SMTP email '%s': %s", subject, exc)
        return EmailDeliveryResult(
            success=False,
            status="failed",
            message=f"SMTP transmission error: {str(exc)}",
            timestamp=now_iso,
        )


def send_contact_inquiry(payload: ContactInquiryPayload) -> EmailDeliveryResult:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "StudySpace AI — New Contact Inquiry"
    body = (
        f"StudySpace AI — New Contact Inquiry\n"
        f"-----------------------------------------\n"
        f"Timestamp:   {now_str}\n"
        f"Name:        {payload.name}\n"
        f"Email:       {payload.email}\n"
        f"Institution: {payload.institution or 'N/A'}\n\n"
        f"Message:\n{payload.message}\n"
        f"-----------------------------------------\n"
    )
    return _send_smtp_email(subject=subject, text_content=body)


def send_developer_access_request(payload: DeveloperAccessRequestPayload) -> EmailDeliveryResult:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "StudySpace AI — Developer API Access Request"
    body = (
        f"StudySpace AI — Developer API Access Request\n"
        f"---------------------------------------------------\n"
        f"Timestamp:            {now_str}\n"
        f"Name:                 {payload.name}\n"
        f"Organization:         {payload.organization}\n"
        f"Email:                {payload.email}\n"
        f"Phone/Contact:        {payload.phone or 'N/A'}\n"
        f"Intended API Use:     {payload.intended_use}\n"
        f"Help/Capability:      {payload.help_needed}\n"
        f"Heard About Us:       {payload.heard_about}\n\n"
        f"Additional Details:\n{payload.additional_message or 'None'}\n"
        f"---------------------------------------------------\n"
    )
    return _send_smtp_email(subject=subject, text_content=body)
