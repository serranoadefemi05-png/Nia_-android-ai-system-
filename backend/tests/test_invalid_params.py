"""Tests: Invalid Tool Parameters"""
import pytest
from fastapi.testclient import TestClient
from ..main import app

client = TestClient(app)
HEADERS = {"X-Device-Id": "param-test-device"}


def test_command_too_long():
    response = client.post(
        "/api/v1/command",
        json={"text": "x" * 2001},
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_command_missing_text():
    response = client.post(
        "/api/v1/command",
        json={},
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_command_non_string_text():
    response = client.post(
        "/api/v1/command",
        json={"text": 12345},
        headers=HEADERS,
    )
    # FastAPI coerces int to string — either 200 or 422 is acceptable
    assert response.status_code in (200, 422)


def test_memory_key_too_long():
    response = client.post(
        "/api/v1/memory",
        json={"key": "k" * 101, "value": "val"},
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_memory_value_too_long():
    response = client.post(
        "/api/v1/memory",
        json={"key": "ok_key", "value": "v" * 10_001},
        headers=HEADERS,
    )
    assert response.status_code == 400


def test_memory_invalid_type():
    response = client.post(
        "/api/v1/memory",
        json={"key": "x", "value": "y", "memory_type": "invalid_type"},
        headers=HEADERS,
    )
    assert response.status_code == 400


def test_forget_nonexistent_entry():
    response = client.delete("/api/v1/memory/mem_000000", headers=HEADERS)
    assert response.status_code == 404


def test_history_limit_param():
    response = client.get("/api/v1/history?limit=5&offset=0", headers=HEADERS)
    assert response.status_code == 200
    assert len(response.json()) <= 5
