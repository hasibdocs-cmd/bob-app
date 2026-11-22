"""
Tests for /api/complaints  (create, list, get, update, rate)
Watsonx calls are patched to return a deterministic local classification.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.conftest import register_user, auth_headers

AI_RESULT = {
    "category": "waterlogging",
    "priority": "high",
    "confidence": 0.9,
    "summary": "Waterlogging issue.",
}


def _make_complaint_payload(**overrides):
    base = {
        "title": "Flood water on the road",
        "description": "There is stagnant flood water near the junction.",
        "category": "waterlogging",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "MG Road, Bengaluru",
    }
    base.update(overrides)
    return base


@pytest.fixture(scope="module")
def citizen_headers(client):
    register_user(client, email="citizen1@example.com", password="pass123", role="citizen")
    return auth_headers(client, email="citizen1@example.com", password="pass123")


@pytest.fixture(scope="module")
def officer_headers(client):
    register_user(client, email="officer1@example.com", password="pass123", role="ward_officer")
    return auth_headers(client, email="officer1@example.com", password="pass123")


# ── Create ────────────────────────────────────────────────────────────────────

class TestCreateComplaint:
    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_create_success(self, _mock, client, citizen_headers):
        resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                           headers=citizen_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Flood water on the road"
        assert data["category"] == "waterlogging"
        assert data["priority"] == "high"
        assert data["status"] == "open"
        assert data["ticket_id"].startswith("NGA-")
        assert data["ai_classification"] == "waterlogging"
        assert data["ai_confidence"] == 0.9
        assert "sla_deadline" in data

    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_create_unauthenticated(self, _mock, client):
        resp = client.post("/api/complaints/", json=_make_complaint_payload())
        assert resp.status_code == 401

    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_create_missing_title(self, _mock, client, citizen_headers):
        payload = _make_complaint_payload()
        del payload["title"]
        resp = client.post("/api/complaints/", json=payload, headers=citizen_headers)
        assert resp.status_code == 422

    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_ticket_id_unique(self, _mock, client, citizen_headers):
        ids = set()
        for _ in range(5):
            resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                               headers=citizen_headers)
            assert resp.status_code == 201
            ids.add(resp.json()["ticket_id"])
        # All 5 ticket IDs should be unique (statistically guaranteed with 10^6 possibilities)
        assert len(ids) == 5


# ── List ──────────────────────────────────────────────────────────────────────

class TestListComplaints:
    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_citizen_sees_own_complaints(self, _mock, client, citizen_headers):
        # Create a complaint as the citizen
        client.post("/api/complaints/", json=_make_complaint_payload(),
                    headers=citizen_headers)
        resp = client.get("/api/complaints/", headers=citizen_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_unauthenticated(self, client):
        resp = client.get("/api/complaints/")
        assert resp.status_code == 401

    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_list_limit_offset(self, _mock, client, citizen_headers):
        resp = client.get("/api/complaints/?limit=2&offset=0", headers=citizen_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


# ── Get ───────────────────────────────────────────────────────────────────────

class TestGetComplaint:
    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_get_existing(self, _mock, client, citizen_headers):
        create_resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                                  headers=citizen_headers)
        complaint_id = create_resp.json()["id"]
        resp = client.get(f"/api/complaints/{complaint_id}", headers=citizen_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == complaint_id

    def test_get_nonexistent(self, client, citizen_headers):
        resp = client.get("/api/complaints/999999", headers=citizen_headers)
        assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

class TestUpdateComplaint:
    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_update_status(self, _mock, client, citizen_headers, officer_headers):
        create_resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                                  headers=citizen_headers)
        complaint_id = create_resp.json()["id"]
        resp = client.patch(f"/api/complaints/{complaint_id}",
                            json={"status": "in_progress", "note": "Working on it"},
                            headers=officer_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_resolve_complaint(self, _mock, client, citizen_headers, officer_headers):
        create_resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                                  headers=citizen_headers)
        complaint_id = create_resp.json()["id"]
        resp = client.patch(f"/api/complaints/{complaint_id}",
                            json={"status": "resolved"},
                            headers=officer_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"
        assert resp.json()["resolved_at"] is not None

    def test_update_nonexistent(self, client, officer_headers):
        resp = client.patch("/api/complaints/999999",
                            json={"status": "resolved"},
                            headers=officer_headers)
        assert resp.status_code == 404


# ── Rate ──────────────────────────────────────────────────────────────────────

class TestRateComplaint:
    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_rate_success(self, _mock, client, citizen_headers):
        create_resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                                  headers=citizen_headers)
        complaint_id = create_resp.json()["id"]
        resp = client.post(f"/api/complaints/{complaint_id}/rate",
                           json={"rating": 4},
                           headers=citizen_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Rating submitted"

    @patch("app.routes.complaints.classify_with_watsonx", new_callable=AsyncMock,
           return_value=AI_RESULT)
    def test_rate_out_of_range(self, _mock, client, citizen_headers):
        create_resp = client.post("/api/complaints/", json=_make_complaint_payload(),
                                  headers=citizen_headers)
        complaint_id = create_resp.json()["id"]
        resp = client.post(f"/api/complaints/{complaint_id}/rate",
                           json={"rating": 6},
                           headers=citizen_headers)
        assert resp.status_code == 400
