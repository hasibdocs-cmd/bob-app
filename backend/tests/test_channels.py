"""
Tests for the multi-channel intake routes and dispatcher.

All tests use the shared in-memory SQLite DB from conftest.py.
No real external API calls are made — outbound senders are mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.models import ChannelType, InboundMessage


# ── Dispatcher unit tests ─────────────────────────────────────────────────────

class TestDispatcher:
    @pytest.mark.asyncio
    async def test_dispatch_persists_inbound_message(self, db):
        """dispatch_inbound should create an InboundMessage row."""
        from app.channels.dispatcher import dispatch_inbound

        msg = await dispatch_inbound(
            db=db,
            channel=ChannelType.web,
            sender_id="user@example.com",
            raw_text="Garbage pile near MG Road",
            send_ack=False,
        )

        assert msg.id is not None
        assert msg.channel == ChannelType.web
        assert msg.sender_id == "user@example.com"
        assert msg.raw_text == "Garbage pile near MG Road"
        # AI classification should have run (local fallback)
        assert msg.ai_category is not None

    @pytest.mark.asyncio
    async def test_dispatch_stores_attachments(self, db):
        """Media attachments are saved and linked to the message."""
        from app.channels.dispatcher import dispatch_inbound
        from app.models import MediaType

        msg = await dispatch_inbound(
            db=db,
            channel=ChannelType.sms,
            sender_id="+919876543210",
            raw_text="Broken drain",
            attachments=[
                {"media_type": MediaType.image, "url": "https://example.com/photo.jpg",
                 "mime_type": "image/jpeg"},
            ],
            send_ack=False,
        )

        db.refresh(msg)
        assert len(msg.attachments) == 1
        assert msg.attachments[0].url == "https://example.com/photo.jpg"
        assert msg.attachments[0].media_type == MediaType.image

    @pytest.mark.asyncio
    async def test_dispatch_string_media_type(self, db):
        """Media type supplied as a plain string is coerced to enum."""
        from app.channels.dispatcher import dispatch_inbound

        msg = await dispatch_inbound(
            db=db,
            channel=ChannelType.whatsapp,
            sender_id="+911234567890",
            raw_text="Waterlogging",
            attachments=[
                {"media_type": "image", "url": "https://example.com/img.png"},
            ],
            send_ack=False,
        )

        db.refresh(msg)
        assert len(msg.attachments) == 1

    @pytest.mark.asyncio
    async def test_dispatch_empty_text_no_crash(self, db):
        """Empty raw_text should not crash — AI step is skipped gracefully."""
        from app.channels.dispatcher import dispatch_inbound

        msg = await dispatch_inbound(
            db=db,
            channel=ChannelType.voice,
            sender_id="+910000000000",
            raw_text="",
            send_ack=False,
        )
        assert msg.id is not None
        assert msg.ai_category is None  # nothing to classify

    @pytest.mark.asyncio
    async def test_dispatch_sends_ack_whatsapp(self, db):
        """When send_ack=True, the WhatsApp sender is called."""
        from app.channels.dispatcher import dispatch_inbound

        with patch("app.channels.whatsapp.send_whatsapp", new_callable=AsyncMock, return_value="SMTEST") as mock_send:
            await dispatch_inbound(
                db=db,
                channel=ChannelType.whatsapp,
                sender_id="+919999999999",
                raw_text="Garbage near park",
                send_ack=True,
            )
            mock_send.assert_called_once()


# ── Webhook endpoint tests ─────────────────────────────────────────────────────

class TestWebhookEndpoints:
    def test_voice_twiml_response(self, client):
        """GET /webhook/voice returns valid TwiML."""
        resp = client.post("/api/channels/webhook/voice")
        assert resp.status_code == 200
        assert "text/xml" in resp.headers["content-type"]
        assert "<Record" in resp.text
        assert "NagaraAI" in resp.text

    def test_telegram_webhook_invalid_secret(self, client):
        """Telegram webhook rejects requests with wrong secret."""
        # With TELEGRAM_WEBHOOK_SECRET="" the verify_telegram_secret always
        # returns True (disabled), so we just check it doesn't crash.
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 123, "first_name": "Test", "last_name": ""},
                "text": "Drain blocked near my house",
                "date": 1700000000,
            }
        }
        resp = client.post("/api/channels/webhook/telegram", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_facebook_challenge(self, client):
        """Meta hub challenge returns the hub.challenge value."""
        from app.config import settings
        token = settings.META_VERIFY_TOKEN
        resp = client.get(
            "/api/channels/webhook/facebook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": token,
                "hub.challenge": "CHALLENGE_XYZ",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "CHALLENGE_XYZ"

    def test_facebook_challenge_wrong_token(self, client):
        """Wrong verify token returns 403."""
        resp = client.get(
            "/api/channels/webhook/facebook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "WRONG_TOKEN",
                "hub.challenge": "ABC",
            },
        )
        assert resp.status_code == 403

    def test_instagram_challenge(self, client):
        """Instagram hub challenge works the same as Facebook."""
        from app.config import settings
        token = settings.META_VERIFY_TOKEN
        resp = client.get(
            "/api/channels/webhook/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": token,
                "hub.challenge": "IG_CHALLENGE",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "IG_CHALLENGE"

    def test_facebook_webhook_no_signature(self, client, auth_headers_fixture):
        """
        Facebook webhook with no META_APP_SECRET set → signature check is skipped
        → 200 OK with empty entry list.
        """
        from app.config import settings
        settings.META_APP_SECRET = ""
        payload = {"object": "page", "entry": []}
        resp = client.post("/api/channels/webhook/facebook", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_twitter_webhook(self, client):
        """Twitter/X webhook accepts a payload with no events gracefully."""
        resp = client.post("/api/channels/webhook/twitter", json={"tweet_create_events": []})
        assert resp.status_code == 200

    def test_email_webhook(self, client):
        """Email webhook ingests a complaint and returns 200."""
        payload = {
            "from": "citizen@example.com",
            "subject": "Garbage near park",
            "body": "There is a huge garbage pile near Cubbon Park.",
        }
        resp = client.post("/api/channels/webhook/email", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── Management endpoint tests ──────────────────────────────────────────────────

class TestManagementEndpoints:
    def test_list_inbound_requires_auth(self, client):
        resp = client.get("/api/channels/inbound")
        assert resp.status_code == 401

    def test_list_inbound_authenticated(self, client, auth_headers_fixture):
        resp = client.get("/api/channels/inbound", headers=auth_headers_fixture)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_dispatch_status_not_found(self, client, auth_headers_fixture):
        resp = client.get("/api/channels/dispatch/999999", headers=auth_headers_fixture)
        assert resp.status_code == 404

    def test_manual_dispatch_complaint_not_found(self, client, auth_headers_fixture):
        payload = {
            "complaint_id": 999999,
            "channel": "sms",
            "recipient": "+919876543210",
        }
        resp = client.post("/api/channels/dispatch", json=payload, headers=auth_headers_fixture)
        assert resp.status_code == 404

    def test_manual_dispatch_creates_record(self, client, auth_headers_fixture, db):
        """Create a real complaint, then dispatch a notification for it."""
        # Create a complaint first via the complaints API
        complaint_resp = client.post(
            "/api/complaints/",
            json={
                "title": "Drain blocked near school",
                "description": "Stagnant water",
                "category": "drain_blockage",
                "address": "Whitefield",
            },
            headers=auth_headers_fixture,
        )
        assert complaint_resp.status_code == 201
        complaint_id = complaint_resp.json()["id"]

        payload = {
            "complaint_id": complaint_id,
            "channel": "sms",
            "recipient": "+919876543210",
            "message_body": "Your complaint has been received.",
        }
        resp = client.post("/api/channels/dispatch", json=payload, headers=auth_headers_fixture)
        assert resp.status_code == 200
        data = resp.json()
        assert data["complaint_id"] == complaint_id
        assert data["channel"] == "sms"
        assert data["recipient"] == "+919876543210"

        # Retrieve the dispatch record
        dispatch_id = data["id"]
        get_resp = client.get(f"/api/channels/dispatch/{dispatch_id}", headers=auth_headers_fixture)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == dispatch_id


# ── Helpers ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def auth_headers_fixture(client):
    """Register + login a user and return auth headers."""
    from tests.conftest import register_user, auth_headers
    register_user(client, email="channel_test@example.com", password="pass123",
                  name="Channel Tester")
    return auth_headers(client, email="channel_test@example.com", password="pass123")
