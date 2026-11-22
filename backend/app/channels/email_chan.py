"""
Email adapter — SMTP outbound + simple inbound parsing.

Outbound: send_email(to, subject, html_body)
Inbound:  parse_email_report(raw_email_text) → dict for InboundMessage creation
"""
import logging
import smtplib
import email as email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str,
                     complaint_id: Optional[int] = None) -> bool:
    """
    Send an HTML email via configured SMTP.
    Returns True on success, False on failure.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info("[Email] Skipping — SMTP not configured. to=%s", to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [to], msg.as_string())
        logger.info("[Email] Sent to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        logger.error("[Email] Send failed: %s", exc)
        return False


def parse_email_report(raw: str) -> dict:
    """
    Parse a raw RFC 2822 email string into a normalised dict for InboundMessage.
    Extracts sender, subject (used as title), body text, and any attachment URLs.
    """
    msg = email_lib.message_from_string(raw)
    sender = msg.get("From", "")
    subject = msg.get("Subject", "No subject")
    body_parts = []
    attachment_urls = []

    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                body_parts.append(payload.decode("utf-8", errors="replace"))
        elif part.get_filename():
            # In a real system these would be stored to blob storage; we record the filename
            attachment_urls.append(part.get_filename())

    return {
        "sender_id": sender,
        "sender_name": sender.split("<")[0].strip(),
        "raw_text": f"{subject}\n\n" + "\n".join(body_parts),
        "metadata_": {"subject": subject, "attachments": attachment_urls},
    }
