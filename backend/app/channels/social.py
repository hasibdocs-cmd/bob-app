"""
Social media adapters — Facebook, Instagram, Twitter/X.

Each platform uses webhooks for inbound messages and their respective APIs for outbound.

Facebook / Instagram:  Meta Graph API webhooks
Twitter/X:             Account Activity API (v2 filtered stream + webhooks)
"""
import hashlib
import hmac
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v19.0"
TWITTER_API = "https://api.twitter.com/2"


# ── Meta webhook verification ─────────────────────────────────────────────────

def verify_meta_signature(body: bytes, header_signature: str) -> bool:
    """
    Validate X-Hub-Signature-256 from Meta webhook.
    header_signature is in the form 'sha256=<hex>'
    """
    if not settings.META_APP_SECRET:
        return True  # verification disabled
    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, header_signature)


# ── Facebook Messenger outbound ───────────────────────────────────────────────

async def send_facebook_message(recipient_id: str, text: str,
                                 complaint_id: Optional[int] = None) -> Optional[str]:
    """Send a text reply via Facebook Messenger. Returns message_id or None."""
    if not settings.META_PAGE_ACCESS_TOKEN:
        logger.info("[Facebook] Skipping — page token not configured.")
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{GRAPH_API}/me/messages",
                params={"access_token": settings.META_PAGE_ACCESS_TOKEN},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            resp.raise_for_status()
            mid = resp.json().get("message_id")
            logger.info("[Facebook] Sent mid=%s to psid=%s", mid, recipient_id)
            return mid
    except Exception as exc:
        logger.error("[Facebook] Send failed: %s", exc)
        return None


# ── Instagram DM outbound ─────────────────────────────────────────────────────

async def send_instagram_message(recipient_id: str, text: str,
                                  complaint_id: Optional[int] = None) -> Optional[str]:
    """Send a text reply via Instagram Direct. Returns message_id or None."""
    if not settings.META_IG_ACCESS_TOKEN:
        logger.info("[Instagram] Skipping — IG token not configured.")
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{GRAPH_API}/me/messages",
                params={"access_token": settings.META_IG_ACCESS_TOKEN},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            resp.raise_for_status()
            mid = resp.json().get("message_id")
            logger.info("[Instagram] Sent mid=%s to igid=%s", mid, recipient_id)
            return mid
    except Exception as exc:
        logger.error("[Instagram] Send failed: %s", exc)
        return None


# ── Twitter/X outbound ────────────────────────────────────────────────────────

async def send_twitter_dm(recipient_id: str, text: str,
                           complaint_id: Optional[int] = None) -> Optional[str]:
    """Send a Twitter/X Direct Message using OAuth1 user context. Returns dm_id or None."""
    if not all([settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET,
                settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_SECRET]):
        logger.info("[Twitter] Skipping — credentials not configured.")
        return None
    try:
        from requests_oauthlib import OAuth1Session
        oauth = OAuth1Session(
            settings.TWITTER_API_KEY,
            client_secret=settings.TWITTER_API_SECRET,
            resource_owner_key=settings.TWITTER_ACCESS_TOKEN,
            resource_owner_secret=settings.TWITTER_ACCESS_SECRET,
        )
        resp = oauth.post(
            f"{TWITTER_API}/dm_conversations/with/{recipient_id}/messages",
            json={"text": text},
        )
        dm_id = resp.json().get("dm_conversation_id")
        logger.info("[Twitter] DM sent dm_id=%s to=%s", dm_id, recipient_id)
        return dm_id
    except Exception as exc:
        logger.error("[Twitter] DM failed: %s", exc)
        return None


# ── Helpers for parsing inbound social payloads ───────────────────────────────

def extract_facebook_messages(payload: dict) -> list[dict]:
    """
    Walk a Meta webhook entry array and extract individual messaging events.
    Returns list of dicts: {sender_id, text, attachments:[{type, url}]}
    """
    results = []
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id", "")
            msg = event.get("message", {})
            text = msg.get("text", "")
            attachments = [
                {"type": a.get("type"), "url": a.get("payload", {}).get("url")}
                for a in msg.get("attachments", [])
            ]
            results.append({"sender_id": sender, "text": text, "attachments": attachments})
    return results


def extract_instagram_messages(payload: dict) -> list[dict]:
    """Same structure as Facebook — Meta uses identical webhook format for IG."""
    return extract_facebook_messages(payload)


def extract_twitter_mentions(payload: dict) -> list[dict]:
    """
    Parse a Twitter Account Activity API webhook body for mention events.
    Returns list of dicts: {sender_id, sender_name, text}
    """
    results = []
    for event in payload.get("tweet_create_events", []):
        results.append({
            "sender_id": str(event.get("user", {}).get("id_str", "")),
            "sender_name": event.get("user", {}).get("screen_name", ""),
            "text": event.get("text", ""),
            "external_id": event.get("id_str", ""),
        })
    return results
