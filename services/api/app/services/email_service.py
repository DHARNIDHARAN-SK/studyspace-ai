from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
from typing import Any, Dict, Optional
import httpx
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
    status: str  # "delivered" | "unconfigured" | "failed"
    message: str
    timestamp: str


def _send_resend_email(
    subject: str, text_content: str, to_email: str = TARGET_NOTIFICATION_EMAIL
) -> Optional[EmailDeliveryResult]:
    """Dispatches email via Resend API if RESEND_API_KEY is configured in the environment."""
    resend_api_key = os.environ.get("RESEND_API_KEY") or getattr(settings, "RESEND_API_KEY", None)
    if not resend_api_key:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    from_email = os.environ.get("RESEND_FROM_EMAIL", "StudySpace AI <onboarding@resend.dev>")
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": text_content,
    }

    try:
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post("https://api.resend.com/emails", json=payload, headers=headers)
            if resp.status_code in (200, 201):
                logger.info("Successfully delivered email via Resend to %s", to_email)
                return EmailDeliveryResult(
                    success=True,
                    status="delivered",
                    message=f"Email successfully delivered to {to_email} via Resend.",
                    timestamp=now_iso,
                )
            else:
                logger.error("Resend API rejected email: %d %s", resp.status_code, resp.text)
                return EmailDeliveryResult(
                    success=False,
                    status="failed",
                    message=f"Resend API error ({resp.status_code}): {resp.text}",
                    timestamp=now_iso,
                )
    except Exception as exc:
        logger.error("Resend delivery exception: %s", exc)
        return EmailDeliveryResult(
            success=False,
            status="failed",
            message=f"Resend transmission failed: {str(exc)}",
            timestamp=now_iso,
        )


def _send_smtp_email(
    subject: str, text_content: str, to_email: str = TARGET_NOTIFICATION_EMAIL
) -> Optional[EmailDeliveryResult]:
    """Dispatches email via SMTP if credentials are fully configured."""
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("SMTP_FROM_EMAIL", smtp_user or "notifications@studyspace.ai")
    now_iso = datetime.now(timezone.utc).isoformat()

    if not smtp_host or not smtp_pass:
        return None

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

        logger.info("Successfully delivered email '%s' via SMTP to %s", subject, to_email)
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


def dispatch_email(
    subject: str, text_content: str, to_email: Optional[str] = None
) -> EmailDeliveryResult:
    """
    Dispatches email notification using configured provider:
    1. Resend API (preferred)
    2. SMTP server
    3. Truthful unconfigured error state (never pretends success)
    """
    target = to_email or os.environ.get("CONTACT_EMAIL", TARGET_NOTIFICATION_EMAIL)
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Try Resend if configured
    resend_res = _send_resend_email(subject, text_content, target)
    if resend_res is not None:
        return resend_res

    # 2. Try SMTP if configured
    smtp_res = _send_smtp_email(subject, text_content, target)
    if smtp_res is not None:
        return smtp_res

    # 3. Neither configured: Truthful unconfigured error
    logger.warning("Email provider not configured. Recorded inquiry for %s: %s", target, subject)
    return EmailDeliveryResult(
        success=False,
        status="unconfigured",
        message=f"Email delivery is not configured on the server. Please contact {target} directly.",
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
    return dispatch_email(subject=subject, text_content=body)


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
    return dispatch_email(subject=subject, text_content=body)
