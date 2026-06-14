"""Tests for the FastAPI layer using dependency overrides (offline)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api
from tests.conftest import StubProvider


@pytest.fixture
def client(settings, baseline_attractions, analytics):
    """Build a TestClient with all external dependencies overridden."""
    from core.schema import KBStatus

    api.app.dependency_overrides[api.get_settings_dep] = lambda: settings
    api.app.dependency_overrides[api.get_provider_dep] = lambda: StubProvider()
    api.app.dependency_overrides[api.get_kb_dep] = lambda: (
        baseline_attractions,
        KBStatus.FRESH,
    )
    api.app.dependency_overrides[api.get_analytics_dep] = lambda: analytics
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["attractions_loaded"] == 12


def test_attractions(client):
    resp = client.get("/attractions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 12
    assert "louvre" in body["attractions"]


def test_ask_on_topic(client):
    resp = client.post("/ask", json={"query": "grand mosque hours", "persona": "first_time"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["off_topic"] is False
    assert body["attraction_id"] == "zayed_mosque"


def test_ask_off_topic_bypasses_llm(client):
    resp = client.post("/ask", json={"query": "write me a python function"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["off_topic"] is True
    assert body["provider"] == "none"


def test_analytics_after_queries(client):
    client.post("/ask", json={"query": "louvre tickets"})
    client.post("/ask", json={"query": "weather in tokyo"})
    resp = client.get("/analytics")
    assert resp.status_code == 200
    assert resp.json()["total_queries"] == 2
