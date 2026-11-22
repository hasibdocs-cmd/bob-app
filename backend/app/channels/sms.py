"""
SMS / MMS adapter — uses Twilio Programmable Messaging.

Inbound:  POST /api/channels/webhook/sms   (Twilio form-encoded webhook)
Outbound: send_sms(to, body) / send_mms(to, body, media_url)
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


def _twilio_client():
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return None
    try:
        from twilio.rest import Client
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    except ImportError:
        logger.warning("twilio package not installed — SMS/MMS outbound disabled")
        return None


async def send_sms(to: str, body: str, complaint_id: Optional[int] = None) -> Optional[str]:
    """Send a plain SMS. Returns Twilio SID or None."""
    client = _twilio_client()
    if not client:
        logger.info("[SMS] Skipping — Twilio not configured. to=%s", to)
        return None
    try:
        message = client.messages.create(
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to,
            body=body,
        )
        logger.info("[SMS] Sent SID=%s to=%s", message.sid, to)
        return message.sid
    except Exception as exc:
        logger.error("[SMS] Send failed: %s", exc)
        return None


async def send_mms(to: str, body: str, media_url: str,
                   complaint_id: Optional[int] = None) -> Optional[str]:
    """Send an MMS with a media attachment. Returns Twilio SID or None."""
    client = _twilio_client()
    if not client:
        logger.info("[MMS] Skipping — Twilio not configured. to=%s", to)
        return None
    try:
        message = client.messages.create(
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to,
            body=body,
            media_url=[media_url],
        )
        logger.info("[MMS] Sent SID=%s to=%s", message.sid, to)
        return message.sid
    except Exception as exc:
        logger.error("[MMS] Send failed: %s", exc)
        return None
