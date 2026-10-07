"""
NIA Backend — Browser Agent Integration Boundary

This module defines the clean adapter boundary for plugging in an external
browser-agent execution system (e.g. "dejevu") in the future.

v0.1: All types are defined; the concrete implementation is a stub.
To integrate Dejevu or another system, implement BrowserAgentProvider
and pass it to get_browser_agent().

DO NOT tightly couple NIA to any third-party browser-agent here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BrowserAgentStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BrowserAgentAction:
    """A single browser interaction step."""
    action_type: str                    # "navigate" | "click" | "fill" | "extract" | "screenshot"
    target: str                         # URL or CSS selector
    value: Optional[str] = None         # For fill actions
    description: str = ""
    timeout_ms: int = 30_000


@dataclass
class BrowserAgentResult:
    status: BrowserAgentStatus
    url: str
    title: str = ""
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    actions_performed: List[str] = field(default_factory=list)
    verified: bool = False


class BrowserAgentProvider:
    """
    Abstract interface. All browser-agent implementations extend this.
    """

    def search(self, query: str, num_results: int = 5) -> BrowserAgentResult:
        raise NotImplementedError

    def browse(self, url: str) -> BrowserAgentResult:
        raise NotImplementedError

    def extract(self, url: str, selectors: List[str]) -> BrowserAgentResult:
        raise NotImplementedError

    def interact(self, url: str, actions: List[BrowserAgentAction]) -> BrowserAgentResult:
        """Execute a sequence of browser actions on a page."""
        raise NotImplementedError

    def verify(self, url: str, condition: str) -> BrowserAgentResult:
        """Verify a condition on a page (e.g. element present, text visible)."""
        raise NotImplementedError


class BrowserAgentVerifier:
    """Post-action verification helper."""

    @staticmethod
    def verify_result(result: BrowserAgentResult, expected_status: BrowserAgentStatus = BrowserAgentStatus.SUCCESS) -> bool:
        return result.status == expected_status and not result.error


# ── Stub implementation ────────────────────────────────────────────────────

class StubBrowserAgent(BrowserAgentProvider):
    """
    Placeholder for v0.1. Returns not-implemented results.
    Replace with DejevuBrowserAgent or PlaywrightBrowserAgent in v0.2.
    """

    def search(self, query: str, num_results: int = 5) -> BrowserAgentResult:
        return BrowserAgentResult(
            status=BrowserAgentStatus.FAILED,
            url="",
            error="Browser agent not configured. Set WEB_AGENT_PROVIDER=dejevu in .env.",
        )

    def browse(self, url: str) -> BrowserAgentResult:
        return BrowserAgentResult(status=BrowserAgentStatus.FAILED, url=url, error="Not implemented in v0.1.")

    def extract(self, url: str, selectors: List[str]) -> BrowserAgentResult:
        return BrowserAgentResult(status=BrowserAgentStatus.FAILED, url=url, error="Not implemented in v0.1.")

    def interact(self, url: str, actions: List[BrowserAgentAction]) -> BrowserAgentResult:
        return BrowserAgentResult(status=BrowserAgentStatus.FAILED, url=url, error="Not implemented in v0.1.")

    def verify(self, url: str, condition: str) -> BrowserAgentResult:
        return BrowserAgentResult(status=BrowserAgentStatus.FAILED, url=url, error="Not implemented in v0.1.")


def get_browser_agent(provider: str = "stub") -> BrowserAgentProvider:
    if provider == "stub":
        return StubBrowserAgent()
    # Future:
    # elif provider == "dejevu": from .dejevu_adapter import DejevuBrowserAgent; return DejevuBrowserAgent()
    # elif provider == "playwright": from .playwright_adapter import PlaywrightBrowserAgent; return PlaywrightBrowserAgent()
    raise ValueError(f"Unknown browser agent provider: {provider!r}")
