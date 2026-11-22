"""
Central dispatcher — receives a normalised inbound message, runs AI classification,
persists it to the DB, and sends an acknowledgement back to the citizen.

Usage (from a webhook handler)::

    msg = await dispatch_inbound(
        db=db,
        channel=ChannelType.whatsapp,
        sender_id="+919876543210",
        raw_text="There's a huge garbage pile near MG Road",
        attachments=[{"media_type": MediaType.image, "url": "https://..."}],
        metadata={"MessageSid": "SM123"},
    )
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import (
    ChannelType,
    InboundMessage,
    MediaAttachment,
    MediaType,
)
from app.watsonx import classify_with_watsonx

logger = logging.getLogger(__name__)

# ── Acknowledgement templates ──────────────────────────────────────────────────

_ACK = {
    ChannelType.whatsapp: (
        "✅ NagaraAI received your report! "
        "Our team is classifying it now. "
        "You'll get a ticket number shortly. 🙏"
    ),
    ChannelType.telegram: (
        "✅ Report received by NagaraAI. "
        "We'll classify and log it right away."
    ),
    ChannelType.sms: "NagaraAI: Got your report. Ticket coming soon.",
    ChannelType.mms: "NagaraAI: Got your report with media. Ticket coming soon.",
    ChannelType.email: (
        "Thank you for contacting NagaraAI Bengaluru. "
        "Your complaint has been received and will be classified shortly."
    ),
    ChannelType.voice: "Thank you. Your complaint has been recorded by NagaraAI.",
    ChannelType.facebook: (
        "✅ NagaraAI received your message. "
        "We'll log your complaint shortly."
    ),
    ChannelType.instagram: (
        "✅ Report received! NagaraAI will process your complaint shortly."
    ),
    ChannelType.twitter_x: (
        "@user NagaraAI has received your report. "
        "We'll log and assign it shortly."
    ),
    ChannelType.web: "Report received.",
    ChannelType.api: "Report received.",
}

_DEFAULT_ACK = "NagaraAI: Report received. Thank you."


def _ack_text(channel: ChannelType) -> str:
    return _ACK.get(channel, _DEFAULT_ACK)


# ── Outbound dispatcher (send ack back) ────────────────────────────────────────

async def _send_ack(channel: ChannelType, sender_id: str, text: str) -> None:
    """Fire-and-forget: send acknowledgement on the same channel the citizen used."""
    try:
        if channel == ChannelType.whatsapp:
            from app.channels.whatsapp import send_whatsapp
            await send_whatsapp(sender_id, text)

        elif channel in (ChannelType.sms, ChannelType.mms):
            from app.channels.sms import send_sms
            await send_sms(sender_id, text)

        elif channel == ChannelType.telegram:
            from app.channels.telegram import send_telegram
            await send_telegram(sender_id, text)

        elif channel == ChannelType.email:
            from app.channels.email_chan import send_email
            await send_email(sender_id, "NagaraAI — Complaint Received", text)

        elif channel == ChannelType.facebook:
            from app.channels.social import send_facebook_message
            await send_facebook_message(sender_id, text)

        elif channel == ChannelType.instagram:
            from app.channels.social import send_instagram_message
            await send_instagram_message(sender_id, text)

        elif channel == ChannelType.twitter_x:
            from app.channels.social import send_twitter_dm
            await send_twitter_dm(sender_id, text)

        # voice / web / api — no ack needed here (TwiML handles voice inline)

    except Exception as exc:
        logger.warning("[Dispatcher] Ack failed on %s to %s: %s", channel, sender_id, exc)


# ── Main entry point ──────────────────────────────────────────────────────────

async def dispatch_inbound(
    *,
    db: Session,
    channel: ChannelType,
    sender_id: str,
    raw_text: str = "",
    sender_name: Optional[str] = None,
    external_id: Optional[str] = None,
    language: str = "en",
    ai_transcript: Optional[str] = None,       # pre-filled for voice→text
    location_text: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    attachments: Optional[list[dict[str, Any]]] = None,  # list of {media_type, url, mime_type?}
    metadata: Optional[dict[str, Any]] = None,
    send_ack: bool = True,
) -> InboundMessage:
    """
    Persist an inbound message, run AI classification, optionally send an ack.

    Returns the saved InboundMessage ORM object (without the linked Complaint yet —
    a background task or staff member will promote it to a full Complaint).
    """
    # ── Classify with watsonx (or local fallback) ──────────────────────────────
    classify_text = ai_transcript or raw_text or ""
    ai_result: dict[str, Any] = {}
    if classify_text.strip():
        try:
            ai_result = await classify_with_watsonx(classify_text)
        except Exception as exc:
            logger.warning("[Dispatcher] AI classification failed: %s", exc)

    # ── Persist InboundMessage ─────────────────────────────────────────────────
    msg = InboundMessage(
        channel=channel,
        external_id=external_id,
        sender_id=sender_id,
        sender_name=sender_name,
        raw_text=raw_text or None,
        language=language,
        ai_transcript=ai_transcript,
        ai_summary=ai_result.get("summary"),
        ai_category=ai_result.get("category"),
        ai_priority=ai_result.get("priority"),
        ai_confidence=ai_result.get("confidence"),
        location_text=location_text,
        latitude=latitude,
        longitude=longitude,
        metadata_=metadata or {},
        is_processed=False,
    )
    db.add(msg)
    db.flush()   # get msg.id before adding children

    # ── Persist media attachments ──────────────────────────────────────────────
    for att in (attachments or []):
        media_type = att.get("media_type", MediaType.image)
        # accept both enum values and plain strings
        if isinstance(media_type, str):
            media_type = MediaType(media_type)
        db.add(MediaAttachment(
            message_id=msg.id,
            media_type=media_type,
            url=att["url"],
            mime_type=att.get("mime_type"),
            file_size_bytes=att.get("file_size_bytes"),
        ))

    db.commit()
    db.refresh(msg)

    logger.info(
        "[Dispatcher] Saved InboundMessage id=%d channel=%s sender=%s "
        "category=%s priority=%s",
        msg.id, channel, sender_id,
        ai_result.get("category", "?"), ai_result.get("priority", "?"),
    )

    # ── Send acknowledgement ───────────────────────────────────────────────────
    if send_ack and sender_id:
        ack = _ack_text(channel)
        await _send_ack(channel, sender_id, ack)

    return msg
