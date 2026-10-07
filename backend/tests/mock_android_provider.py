"""
NIA Backend — Mock Android Tool Provider
Used by tests so the backend test suite does NOT depend on a physical device.

Implements the same tool execution interface the real Android client uses when it
receives a dispatched_to_client result from the ToolExecutor.

Each mock tool returns a realistic success response and records the call
so tests can assert on what was invoked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class MockCall:
    tool_id: str
    parameters: Dict[str, Any]
    called_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MockAndroidProvider:
    """
    Drop-in replacement for the Android client in tests.
    Simulates the full round-trip: the backend dispatches a tool call,
    the Android client executes it, and returns a result.
    """

    def __init__(self) -> None:
        self.calls: List[MockCall] = []
        self._fail_tools: set = set()  # Tools that should simulate failure

    def fail_next(self, tool_id: str) -> None:
        """Tell the mock to return a failure for the next call to tool_id."""
        self._fail_tools.add(tool_id)

    def execute(self, tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Android executing the tool and returning a result."""
        self.calls.append(MockCall(tool_id=tool_id, parameters=parameters))

        if tool_id in self._fail_tools:
            self._fail_tools.discard(tool_id)
            return {"error": f"Mock Android failure for tool '{tool_id}'"}

        handlers = {
            "take_screenshot": self._take_screenshot,
            "search_local_files": self._search_local_files,
            "create_reminder": self._create_reminder,
            "web_search": self._web_search,
            "open_app": self._open_app,
            "read_selected_notification": self._read_notification,
            "send_message": self._send_message,
            "delete_file": self._delete_file,
            "make_payment": self._make_payment_stub,
        }

        handler = handlers.get(tool_id)
        if handler is None:
            return {"error": f"Unknown tool in mock Android provider: '{tool_id}'"}
        return handler(parameters)

    # -------------------------------------------------------------------------
    # Tool-specific mock responses
    # -------------------------------------------------------------------------

    def _take_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "path": "/storage/emulated/0/Pictures/Screenshots/NIA_20261006_090000.png",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "width": 1080,
            "height": 2400,
        }

    def _search_local_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_type = params.get("file_type", "pdf")
        return {
            "files": [
                {
                    "name": f"document_{i}.{file_type}",
                    "path": f"/storage/emulated/0/Download/document_{i}.{file_type}",
                    "size_bytes": 204800 * i,
                    "modified": "2026-10-05T14:22:00Z",
                }
                for i in range(1, 4)
            ],
            "count": 3,
        }

    def _create_reminder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reminder_id": "rem_mock_001",
            "confirmed": True,
            "title": params.get("title", "Reminder"),
            "datetime_iso": params.get("datetime_iso", "2026-10-07T09:00:00Z"),
        }

    def _web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        return {
            "results": [
                {
                    "title": f"Result 1 for: {query}",
                    "url": "https://duckduckgo.com",
                    "snippet": f"Information about {query}.",
                },
                {
                    "title": f"Result 2 for: {query}",
                    "url": "https://wikipedia.org",
                    "snippet": f"More information about {query}.",
                },
            ],
            "summary": f"Here are the top results for '{query}'.",
        }

    def _open_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "opened": True,
            "package_name": f"com.mock.{params.get('app_name', 'app').lower()}",
        }

    def _read_notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": "Mock Notification",
            "body": "This is a mock notification body.",
            "app": "com.mock.app",
        }

    def _send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sent": True,
            "message_id": "msg_mock_001",
        }

    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"deleted": True}

    def _make_payment_stub(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Payments always require confirmation — this should never be called without it
        return {
            "status": "requires_user_confirmation",
            "transaction_id": None,
        }

    # -------------------------------------------------------------------------
    # Test helpers
    # -------------------------------------------------------------------------

    def was_called(self, tool_id: str) -> bool:
        return any(c.tool_id == tool_id for c in self.calls)

    def call_count(self, tool_id: str) -> int:
        return sum(1 for c in self.calls if c.tool_id == tool_id)

    def reset(self) -> None:
        self.calls.clear()
        self._fail_tools.clear()
