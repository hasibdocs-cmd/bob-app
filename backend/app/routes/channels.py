"""
Multi-channel intake & dispatch routes.

Webhook endpoints (all unauthenticated — verified via platform signatures):
  POST /api/channels/webhook/whatsapp
  POST /api/channels/webhook/sms
  POST /api/channels/webhook/voice
  POST /api/channels/webhook/voice/transcription
  POST /api/channels/webhook/telegram
  GET  /api/channels/webhook/facebook   (Meta hub challenge)
  POST /api/channels/webhook/facebook
  GET  /api/channels/webhook/instagram  (Meta hub challenge)
  POST /api/channels/webhook/instagram
  POST /api/channels/webhook/twitter
  POST /api/channels/webhook/email

Management endpoints (authenticated):
  POST /api/channels/dispatch          — manually send a notification
  GET  /api/channels/inbound           — list inbound messages
  GET  /api/channels/dispatch/{id}     — dispatch status
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ChannelDispatch,
    ChannelType,
    InboundMessage,
    MediaType,
)
from app.schemas import (
    ChannelDispatchOut,
    DispatchRequest,
    InboundMessageOut,
    MetaWebhookPayload,
    TelegramUpdate,
)
from app.auth import get_current_user  # re-use existing JWT dep
from app.channels.dispatcher import dispatch_inbound
from app.config import settings

router = APIRouter(prefix="/api/channels", tags=["channels"])
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _twilio_attachments(form: dict) -> list[dict]:
    """Extract Twilio media attachments from form data."""
    attachments = []
    num = int(form.get("NumMedia", 0))
    for i in range(num):
        url = form.get(f"MediaUrl{i}")
        mime = form.get(f"MediaContentType{i}", "")
        if url:
            media_type = MediaType.image
            if mime.startswith("audio"):
                media_type = MediaType.audio
            elif mime.startswith("video"):
                media_type = MediaType.video
            elif mime.startswith("application"):
                media_type = MediaType.document
            attachments.append({"media_type": media_type, "url": url, "mime_type": mime})
    return attachments


# ── WhatsApp webhook (Twilio) ─────────────────────────────────────────────────

@router.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())

    # Signature verification (skipped when TWILIO_VERIFY_SIGNATURE=False)
    from app.channels.whatsapp import verify_twilio_signature
    sig = request.headers.get("X-Twilio-Signature", "")
    if not verify_twilio_signature(str(request.url), form, sig):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    sender = form.get("From", "").replace("whatsapp:", "")
    await dispatch_inbound(
        db=db,
        channel=ChannelType.whatsapp,
        sender_id=sender,
        raw_text=form.get("Body", ""),
        external_id=form.get("MessageSid"),
        attachments=_twilio_attachments(form),
        metadata=dict(form),
    )
    # Twilio expects an empty 200 or TwiML
    return Response(content="", media_type="text/xml")


# ── SMS webhook (Twilio) ──────────────────────────────────────────────────────

@router.post("/webhook/sms")
async def webhook_sms(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    from app.channels.whatsapp import verify_twilio_signature
    sig = request.headers.get("X-Twilio-Signature", "")
    if not verify_twilio_signature(str(request.url), form, sig):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    num_media = int(form.get("NumMedia", 0))
    channel = ChannelType.mms if num_media > 0 else ChannelType.sms
    await dispatch_inbound(
        db=db,
        channel=channel,
        sender_id=form.get("From", ""),
        raw_text=form.get("Body", ""),
        external_id=form.get("MessageSid"),
        attachments=_twilio_attachments(form),
        metadata=dict(form),
    )
    return Response(content="", media_type="text/xml")


# ── Voice webhook (Twilio) ────────────────────────────────────────────────────

@router.post("/webhook/voice")
async def webhook_voice(request: Request):
    """Return TwiML to record the caller's message."""
    record_url = f"{settings.APP_BASE_URL}/api/channels/webhook/voice/transcription"
    twiml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Response>"
        "<Say language='en-IN'>Welcome to NagaraAI. Please describe your civic issue after the beep.</Say>"
        f"<Record maxLength='120' transcribe='true' transcribeCallback='{record_url}'/>"
        "<Say>Thank you. Your complaint has been recorded. Goodbye.</Say>"
        "</Response>"
    )
    return Response(content=twiml, media_type="text/xml")


@router.post("/webhook/voice/transcription")
async def webhook_voice_transcription(request: Request, db: Session = Depends(get_db)):
    """Twilio posts transcription result here after recording finishes."""
    form = dict(await request.form())
    transcript = form.get("TranscriptionText", "")
    caller = form.get("From", "")
    await dispatch_inbound(
        db=db,
        channel=ChannelType.voice,
        sender_id=caller,
        raw_text="",
        ai_transcript=transcript,
        external_id=form.get("CallSid"),
        metadata=dict(form),
        send_ack=False,  # voice ack is handled by TwiML <Say> above
    )
    return Response(content="", media_type="text/xml")


# ── Telegram webhook ──────────────────────────────────────────────────────────

@router.post("/webhook/telegram")
async def webhook_telegram(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    from app.channels.telegram import verify_telegram_secret
    if not verify_telegram_secret(b"", x_telegram_bot_api_secret_token or ""):
        raise HTTPException(status_code=403, detail="Invalid Telegram secret")

    msg = update.message or update.channel_post or {}
    chat = msg.get("chat", {})
    sender = msg.get("from", {})
    text = msg.get("text", "")
    chat_id = str(chat.get("id", ""))
    sender_name = sender.get("first_name", "") + " " + sender.get("last_name", "")

    attachments = []
    for media_key, media_type in [("photo", MediaType.image), ("video", MediaType.video),
                                   ("audio", MediaType.audio), ("document", MediaType.document)]:
        if media_key in msg:
            # For photos, pick the largest size
            item = msg[media_key]
            if isinstance(item, list):
                item = item[-1]
            file_id = item.get("file_id", "")
            # We store file_id as URL — a real impl would call getFile to resolve it
            attachments.append({
                "media_type": media_type,
                "url": f"tg://file/{file_id}",
            })

    await dispatch_inbound(
        db=db,
        channel=ChannelType.telegram,
        sender_id=chat_id,
        sender_name=sender_name.strip(),
        raw_text=text,
        external_id=str(update.update_id),
        attachments=attachments,
        metadata={"chat_id": chat_id},
    )
    return {"ok": True}


# ── Facebook webhook ──────────────────────────────────────────────────────────

@router.get("/webhook/facebook")
async def facebook_challenge(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """Meta webhook subscription verification."""
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/facebook")
async def webhook_facebook(
    payload: MetaWebhookPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.channels.social import verify_meta_signature, extract_facebook_messages
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_meta_signature(body, sig):
        raise HTTPException(status_code=403, detail="Invalid Meta signature")

    for ev in extract_facebook_messages(payload.model_dump()):
        if ev["sender_id"]:
            atts = [
                {"media_type": MediaType.image if a["type"] == "image" else MediaType.video,
                 "url": a["url"]}
                for a in ev.get("attachments", []) if a.get("url")
            ]
            await dispatch_inbound(
                db=db,
                channel=ChannelType.facebook,
                sender_id=ev["sender_id"],
                raw_text=ev.get("text", ""),
                attachments=atts,
            )
    return {"status": "ok"}


# ── Instagram webhook ─────────────────────────────────────────────────────────

@router.get("/webhook/instagram")
async def instagram_challenge(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/instagram")
async def webhook_instagram(
    payload: MetaWebhookPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.channels.social import verify_meta_signature, extract_instagram_messages
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_meta_signature(body, sig):
        raise HTTPException(status_code=403, detail="Invalid Meta signature")

    for ev in extract_instagram_messages(payload.model_dump()):
        if ev["sender_id"]:
            await dispatch_inbound(
                db=db,
                channel=ChannelType.instagram,
                sender_id=ev["sender_id"],
                raw_text=ev.get("text", ""),
            )
    return {"status": "ok"}


# ── Twitter/X webhook ─────────────────────────────────────────────────────────

@router.post("/webhook/twitter")
async def webhook_twitter(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    from app.channels.social import extract_twitter_mentions
    for ev in extract_twitter_mentions(body):
        if ev["sender_id"]:
            await dispatch_inbound(
                db=db,
                channel=ChannelType.twitter_x,
                sender_id=ev["sender_id"],
                sender_name=ev.get("sender_name"),
                raw_text=ev.get("text", ""),
                external_id=ev.get("external_id"),
            )
    return {"status": "ok"}


# ── Email webhook ─────────────────────────────────────────────────────────────

@router.post("/webhook/email")
async def webhook_email(request: Request, db: Session = Depends(get_db)):
    """
    Accepts a JSON body with {from, subject, body, attachments?}.
    Real deployments point their MTA (e.g. SendGrid Inbound Parse) here.
    """
    data: dict[str, Any] = await request.json()
    sender = data.get("from", "")
    subject = data.get("subject", "")
    body_text = data.get("body", "")
    combined = f"{subject}. {body_text}".strip()

    atts = [
        {"media_type": MediaType.document, "url": a["url"], "mime_type": a.get("mime_type")}
        for a in data.get("attachments", []) if a.get("url")
    ]
    await dispatch_inbound(
        db=db,
        channel=ChannelType.email,
        sender_id=sender,
        raw_text=combined,
        attachments=atts,
        metadata={"subject": subject},
    )
    return {"status": "ok"}


# ── Management endpoints ──────────────────────────────────────────────────────

@router.post("/dispatch", response_model=ChannelDispatchOut)
async def manual_dispatch(
    body: DispatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually send a notification to a citizen on any channel."""
    from app.models import Complaint as ComplaintModel

    complaint = db.query(ComplaintModel).filter(ComplaintModel.id == body.complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    message_body = body.message_body or (
        f"NagaraAI Update — Ticket {complaint.ticket_id}: "
        f"Your complaint '{complaint.title}' is now {complaint.status.value}."
    )

    # Send on the requested channel
    ext_id: Optional[str] = None
    try:
        if body.channel == ChannelType.whatsapp:
            from app.channels.whatsapp import send_whatsapp
            ext_id = await send_whatsapp(body.recipient, message_body, complaint.id)
        elif body.channel in (ChannelType.sms, ChannelType.mms):
            from app.channels.sms import send_sms
            ext_id = await send_sms(body.recipient, message_body)
        elif body.channel == ChannelType.telegram:
            from app.channels.telegram import send_telegram
            ext_id = str(await send_telegram(body.recipient, message_body) or "")
        elif body.channel == ChannelType.email:
            from app.channels.email_chan import send_email
            await send_email(body.recipient, f"NagaraAI Update — {complaint.ticket_id}", message_body)
        elif body.channel == ChannelType.facebook:
            from app.channels.social import send_facebook_message
            ext_id = await send_facebook_message(body.recipient, message_body, complaint.id)
        elif body.channel == ChannelType.instagram:
            from app.channels.social import send_instagram_message
            ext_id = await send_instagram_message(body.recipient, message_body, complaint.id)
        elif body.channel == ChannelType.twitter_x:
            from app.channels.social import send_twitter_dm
            ext_id = await send_twitter_dm(body.recipient, message_body, complaint.id)
    except Exception as exc:
        logger.error("[Dispatch] Send failed: %s", exc)

    dispatch = ChannelDispatch(
        complaint_id=complaint.id,
        channel=body.channel,
        recipient=body.recipient,
        message_body=message_body,
        external_id=ext_id,
        status="sent" if ext_id else "queued",
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)
    return dispatch


@router.get("/inbound", response_model=list[InboundMessageOut])
def list_inbound(
    channel: Optional[ChannelType] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(InboundMessage)
    if channel:
        q = q.filter(InboundMessage.channel == channel)
    return q.order_by(InboundMessage.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/dispatch/{dispatch_id}", response_model=ChannelDispatchOut)
def get_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    d = db.query(ChannelDispatch).filter(ChannelDispatch.id == dispatch_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return d
