"""
Tests for /api/wards  and  /api/analytics
"""
import pytest
from unittest.mock import patch, AsyncMock
from app import models
from tests.conftest import register_user, auth_headers

AI_RESULT = {
    "category": "garbage_black_spot",
    "priority": "medium",
    "confidence": 0.75,
    "summary": "Garbage issue.",
}


@pytest.fixture(scope="module")
def headers(client):
    register_user(client, email="analytics_user@example.com", password="pass123")
    return auth_headers(client, email="analytics_user@example.com", password="pass123")


@pytest.fixture(scope="module")
def seeded_ward(client):
    """Insert a ward directly into the DB via the override session."""
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    ward = models.Ward(name="Test Ward", zone="South", flood_risk_score=3.0,
                       cleanliness_score=80.0)
    db.add(ward)
    db.commit()
    db.refresh(ward)
    ward_id = ward.id
    db.close()
    return ward_id


# ── Wards ─────────────────────────────────────────────────────────────────────

class TestWards:
    def test_list_wards(self, client, seeded_ward):
        resp = client.get("/api/wards/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [w["id"] for w in data]
        assert seeded_ward in ids

    def test_ward_stats(self, client, seeded_ward):
        resp = client.get(f"/api/wards/{seeded_ward}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ward_id"] == seeded_ward
        assert "open_count" in data
        assert "resolved_count" in data
        assert "flood_risk_score" in data


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_city_stats_requires_auth(self, client):
        resp = client.get("/api/analytics/city")
        assert resp.status_code == 401

    def test_city_stats_authenticated(self, client, headers):
        resp = client.get("/api/analytics/city", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_complaints" in data
        assert "open_complaints" in data
        assert "resolved_today" in data
        assert "avg_resolution_hours" in data
        assert "top_category" in data
        assert "high_risk_wards" in data

    def test_city_stats_counts_are_non_negative(self, client, headers):
        resp = client.get("/api/analytics/city", headers=headers)
        data = resp.json()
        assert data["total_complaints"] >= 0
        assert data["open_complaints"] >= 0
        assert data["resolved_today"] >= 0
        assert data["avg_resolution_hours"] >= 0.0

    def test_ward_heatmap(self, client, headers, seeded_ward):
        resp = client.get("/api/analytics/ward-heatmap", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [w["ward_id"] for w in data]
        assert seeded_ward in ids

    def test_contractor_leaderboard(self, client, headers):
        resp = client.get("/api/analytics/contractors", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
