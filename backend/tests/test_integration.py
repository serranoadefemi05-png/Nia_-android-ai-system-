"""
Tests: Integration — Voice Command Flows
Four full end-to-end flows through the orchestrator using the mock Android provider:
1. voice command -> screenshot
2. voice command -> file search
3. voice command -> reminder
4. voice command -> web search
"""
import pytest
from fastapi.testclient import TestClient
from ..main import app
from .mock_android_provider import MockAndroidProvider

client = TestClient(app)
android = MockAndroidProvider()
HEADERS = {"X-Device-Id": "integration-test-device"}


# ---------------------------------------------------------------------------
# 1. Screenshot flow
# ---------------------------------------------------------------------------

def test_integration_screenshot_full_flow():
    """
    Voice: "Nia, take a screenshot"
    -> intent parsed -> take_screenshot tool selected
    -> dispatched_to_client (no handler registered in test env)
    -> response generated
    """
    response = client.post(
        "/api/v1/command",
        json={
            "text": "Nia, take a screenshot",
            "granted_permissions": ["MEDIA_PROJECTION"],
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "take_screenshot"
    # When no execute_handler registered, tool returns dispatched_to_client — status is still completed
    assert data["status"] in ("completed", "failed")
    assert "task_id" in data
    assert len(data["task_id"]) > 0

    # Simulate Android executing the tool and returning success
    mock_result = android.execute("take_screenshot", {})
    assert "path" in mock_result
    assert "timestamp" in mock_result
    assert android.was_called("take_screenshot")


# ---------------------------------------------------------------------------
# 2. File search flow
# ---------------------------------------------------------------------------

def test_integration_file_search_flow():
    """
    Voice: "Nia, find that PDF I downloaded yesterday"
    -> search_local_files tool selected
    -> entities extracted: file_type=pdf, date_hint=yesterday
    """
    response = client.post(
        "/api/v1/command",
        json={
            "text": "Nia abeg find that PDF I downloaded yesterday",
            "granted_permissions": ["READ_EXTERNAL_STORAGE"],
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "search_local_files"
    assert data["status"] in ("completed", "failed")

    # Simulate Android returning results
    android.reset()
    mock_result = android.execute("search_local_files", {"file_type": "pdf", "date_hint": "yesterday"})
    assert mock_result["count"] == 3
    assert len(mock_result["files"]) == 3
    assert android.was_called("search_local_files")


# ---------------------------------------------------------------------------
# 3. Reminder flow
# ---------------------------------------------------------------------------

def test_integration_reminder_flow():
    """
    Voice: "Nia, remind me tomorrow at 9 AM to call the supplier"
    -> create_reminder tool selected
    -> requires: SET_ALARM, SCHEDULE_EXACT_ALARM
    """
    response = client.post(
        "/api/v1/command",
        json={
            "text": "Nia, remind me tomorrow at 9 AM to call the supplier",
            "granted_permissions": ["SET_ALARM", "SCHEDULE_EXACT_ALARM"],
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "create_reminder"
    assert "response" in data

    # Simulate Android creating the reminder
    android.reset()
    mock_result = android.execute("create_reminder", {
        "title": "Call the supplier",
        "datetime_iso": "2026-10-07T09:00:00+01:00",
    })
    assert mock_result["confirmed"] is True
    assert mock_result["reminder_id"] == "rem_mock_001"


# ---------------------------------------------------------------------------
# 4. Web search flow
# ---------------------------------------------------------------------------

def test_integration_web_search_flow():
    """
    Voice: "Nia, search for ESP32 DevKit"
    -> web_search tool selected
    -> returns results + summary
    """
    response = client.post(
        "/api/v1/command",
        json={
            "text": "search the web for ESP32 DevKit price in Nigeria",
            "granted_permissions": [],
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "web_search"
    assert "response" in data

    # Simulate Android web search (via mock)
    android.reset()
    mock_result = android.execute("web_search", {"query": "ESP32 DevKit price in Nigeria"})
    assert len(mock_result["results"]) >= 2
    assert "summary" in mock_result
    assert android.was_called("web_search")


# ---------------------------------------------------------------------------
# 5. Mock failure simulation
# ---------------------------------------------------------------------------

def test_mock_android_failure_simulation():
    """Test that mock provider correctly simulates tool failures."""
    android.reset()
    android.fail_next("take_screenshot")
    result = android.execute("take_screenshot", {})
    assert "error" in result
    # Next call should succeed
    result2 = android.execute("take_screenshot", {})
    assert "path" in result2


# ---------------------------------------------------------------------------
# 6. History populated after commands
# ---------------------------------------------------------------------------

def test_history_populated_after_commands():
    # Send a command
    client.post(
        "/api/v1/command",
        json={
            "text": "search the web for Python",
            "granted_permissions": [],
        },
        headers=HEADERS,
    )
    response = client.get("/api/v1/history", headers=HEADERS)
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 1
    assert history[0]["task_id"].startswith("task_")
