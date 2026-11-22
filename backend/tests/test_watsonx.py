"""
Tests for the local watsonx classifier  (classify_complaint_local)
and the classify_with_watsonx dispatcher.
No network calls are made.
"""
import pytest
from unittest.mock import patch, AsyncMock
from app.watsonx import classify_complaint_local, classify_with_watsonx, SLA_HOURS


# ── classify_complaint_local ──────────────────────────────────────────────────

class TestLocalClassifier:
    def test_garbage_keyword(self):
        result = classify_complaint_local("Garbage dump near school", "")
        assert result["category"] == "garbage_black_spot"
        assert 0.0 <= result["confidence"] <= 1.0

    def test_waterlogging_keyword(self):
        result = classify_complaint_local("Flood water stagnant on road", "overflow on street")
        assert result["category"] == "waterlogging"

    def test_drain_blockage_keyword(self):
        result = classify_complaint_local("Drain is blocked", "manhole clog")
        assert result["category"] == "drain_blockage"

    def test_groundwater_keyword(self):
        result = classify_complaint_local("Borewell dried up", "water shortage in area")
        assert result["category"] == "groundwater"

    def test_cd_waste_keyword(self):
        result = classify_complaint_local("Construction debris on road", "rubble and bricks")
        assert result["category"] == "cd_waste"

    def test_unknown_falls_back_to_other(self):
        result = classify_complaint_local("Random noise complaint", "")
        assert result["category"] == "other"
        assert result["confidence"] == 0.4

    def test_critical_priority_keywords(self):
        result = classify_complaint_local("Emergency flood overflow", "critical situation")
        assert result["priority"] == "critical"

    def test_high_priority_keywords(self):
        result = classify_complaint_local("Dangerous hazard on road", "")
        assert result["priority"] == "high"

    def test_low_priority_keywords(self):
        result = classify_complaint_local("Minor small garbage issue", "")
        assert result["priority"] == "low"

    def test_default_priority_medium(self):
        result = classify_complaint_local("Some complaint", "")
        assert result["priority"] == "medium"

    def test_summary_contains_category(self):
        result = classify_complaint_local("Garbage here", "trash dump")
        assert "garbage_black_spot" in result["summary"]

    def test_confidence_capped_at_one(self):
        # Feed many matching keywords to ensure cap
        result = classify_complaint_local(
            "garbage trash waste dump littering refuse", "black spot")
        assert result["confidence"] <= 1.0

    def test_result_has_required_keys(self):
        result = classify_complaint_local("test", "test")
        assert {"category", "priority", "confidence", "summary"} == set(result.keys())


# ── SLA_HOURS ─────────────────────────────────────────────────────────────────

class TestSLAHours:
    def test_critical_sla(self):
        assert SLA_HOURS["critical"] == 4

    def test_high_sla(self):
        assert SLA_HOURS["high"] == 24

    def test_medium_sla(self):
        assert SLA_HOURS["medium"] == 72

    def test_low_sla(self):
        assert SLA_HOURS["low"] == 168

    def test_all_priorities_covered(self):
        assert set(SLA_HOURS.keys()) == {"critical", "high", "medium", "low"}


# ── classify_with_watsonx dispatcher ──────────────────────────────────────────

class TestWatsonxDispatcher:
    @pytest.mark.asyncio
    async def test_falls_back_when_no_credentials(self):
        """When API key is empty, should use local classifier."""
        from app.config import settings
        original_key = settings.WATSONX_API_KEY
        settings.WATSONX_API_KEY = ""
        try:
            result = await classify_with_watsonx("Garbage dump", "trash everywhere")
            assert result["category"] in {
                "garbage_black_spot", "cd_waste", "waterlogging",
                "drain_blockage", "groundwater", "other"
            }
            assert "priority" in result
            assert "confidence" in result
        finally:
            settings.WATSONX_API_KEY = original_key

    @pytest.mark.asyncio
    async def test_falls_back_on_network_error(self):
        """When the httpx client raises, falls back to local classifier."""
        from app.config import settings
        settings.WATSONX_API_KEY = "fake-key"
        settings.WATSONX_PROJECT_ID = "fake-project"
        try:
            # Patch the async context manager so __aenter__ raises immediately
            mock_client = AsyncMock()
            mock_client.__aenter__.side_effect = Exception("network error")
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await classify_with_watsonx("Flood water", "")
            assert result["category"] in {
                "garbage_black_spot", "cd_waste", "waterlogging",
                "drain_blockage", "groundwater", "other"
            }
        finally:
            settings.WATSONX_API_KEY = ""
            settings.WATSONX_PROJECT_ID = ""
