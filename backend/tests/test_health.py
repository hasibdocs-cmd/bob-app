"""
Tests for the /health endpoint and basic app bootstrap.
"""


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "NagaraAI"

    def test_health_no_auth_required(self, client):
        """Health check must be reachable without a token."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_docs_accessible(self, client):
        """OpenAPI spec should be reachable."""
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "NagaraAI API"
        assert "/api/auth/register" in schema["paths"]
        assert "/api/complaints/" in schema["paths"]
