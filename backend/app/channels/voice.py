"""
Twilio Voice adapter.

Inbound:  POST /api/channels/webhook/voice  (Twilio calls this when a call arrives)
          Returns TwiML to gather speech, which is then transcribed and processed.

Outbound: send_voice_call(to, twiml_url) — programmatic outbound call
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# TwiML template for inbound IVR — greet the caller and record their complaint
INBOUND_TWIML = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="en-IN">
    Welcome to NagaraAI, Bengaluru's civic reporting system.
    Please describe your complaint after the beep. Press any key when done.
  </Say>
  <Record
    action="/api/channels/webhook/voice/transcription"
    transcribe="true"
    transcribeCallback="/api/channels/webhook/voice/transcription"
    maxLength="120"
    finishOnKey="*"
    playBeep="true"
  />
  <Say>Thank you. Your complaint has been recorded and will be processed shortly.</Say>
</Response>"""

STATUS_UPDATE_TWIML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="en-IN">{message}</Say>
</Response>"""


def inbound_twiml() -> str:
    return INBOUND_TWIML


def status_update_twiml(message: str) -> str:
    return STATUS_UPDATE_TWIML_TEMPLATE.format(message=message)


async def send_voice_call(to: str, twiml_url: str,
                          complaint_id: Optional[int] = None) -> Optional[str]:
    """
    Initiate an outbound call to `to` playing TwiML from `twiml_url`.
    Returns call SID or None.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.info("[Voice] Skipping — Twilio not configured. to=%s", to)
        return None
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to,
            url=twiml_url,
        )
        logger.info("[Voice] Call SID=%s to=%s", call.sid, to)
        return call.sid
    except Exception as exc:
        logger.error("[Voice] Call failed: %s", exc)
        return None
