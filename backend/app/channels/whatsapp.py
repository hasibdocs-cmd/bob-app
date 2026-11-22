"""
WhatsApp adapter — uses Twilio's WhatsApp Business API.

Inbound:  POST /api/channels/webhook/whatsapp  (Twilio sends form-encoded data)
Outbound: send_whatsapp(to, body, complaint_id)
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


def _twilio_client():
    """Return a Twilio REST client, or None if credentials are not configured."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return None
    try:
        from twilio.rest import Client
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    except ImportError:
        logger.warning("twilio package not installed — WhatsApp outbound disabled")
        return None


async def send_whatsapp(to: str, body: str, complaint_id: Optional[int] = None) -> Optional[str]:
    """
    Send a WhatsApp message via Twilio.
    `to` must be in E.164 format: +919876543210
    Returns the Twilio SID on success, None on failure.
    """
    client = _twilio_client()
    if not client:
        logger.info("[WhatsApp] Skipping send — Twilio not configured. To: %s | %s", to, body)
        return None
    try:
        from_number = settings.TWILIO_WHATSAPP_NUMBER or f"whatsapp:{settings.TWILIO_PHONE_NUMBER}"
        message = client.messages.create(
            from_=from_number,
            to=f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
            body=body,
        )
        logger.info("[WhatsApp] Sent SID=%s to %s", message.sid, to)
        return message.sid
    except Exception as exc:
        logger.error("[WhatsApp] Send failed: %s", exc)
        return None


def verify_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
    """Verify that the incoming webhook genuinely came from Twilio."""
    if not settings.TWILIO_VERIFY_SIGNATURE:
        return True
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        return validator.validate(request_url, params, signature)
    except Exception:
        return False
