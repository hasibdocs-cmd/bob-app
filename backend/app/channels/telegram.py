"""
Telegram Bot adapter.

Inbound:  POST /api/channels/webhook/telegram  (Telegram pushes Update objects)
Outbound: send_telegram(chat_id, text, complaint_id)
"""
import logging
import hashlib
import hmac
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot"


def _bot_url(method: str) -> str:
    return f"{TELEGRAM_API}{settings.TELEGRAM_BOT_TOKEN}/{method}"


async def send_telegram(chat_id: str, text: str, complaint_id: Optional[int] = None) -> Optional[str]:
    """
    Send a text message to a Telegram chat.
    Returns the message_id string on success, None on failure.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.info("[Telegram] Skipping send — bot token not configured. chat_id=%s", chat_id)
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _bot_url("sendMessage"),
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            resp.raise_for_status()
            data = resp.json()
            msg_id = str(data.get("result", {}).get("message_id", ""))
            logger.info("[Telegram] Sent message_id=%s to chat_id=%s", msg_id, chat_id)
            return msg_id
    except Exception as exc:
        logger.error("[Telegram] Send failed: %s", exc)
        return None


def verify_telegram_secret(body: bytes, header_secret: str) -> bool:
    """Verify the X-Telegram-Bot-Api-Secret-Token header."""
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        return True  # verification disabled
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    return hmac.compare_digest(header_secret, expected)


async def set_webhook(webhook_url: str) -> bool:
    """Register this server's URL as the Telegram webhook (call once at startup)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _bot_url("setWebhook"),
                json={
                    "url": webhook_url,
                    "secret_token": settings.TELEGRAM_WEBHOOK_SECRET or "",
                    "allowed_updates": ["message", "channel_post"],
                },
            )
            ok = resp.json().get("ok", False)
            logger.info("[Telegram] setWebhook ok=%s url=%s", ok, webhook_url)
            return ok
    except Exception as exc:
        logger.error("[Telegram] setWebhook failed: %s", exc)
        return False
