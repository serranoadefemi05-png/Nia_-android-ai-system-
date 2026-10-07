"""
NIA Browser Agent — Provider Abstraction

Inspired by dejevu's Policy ABC and the dejevu OPERATIONS allowlist (types.py).

The BrowserAgentProvider ABC defines the contract that all browser backends must
satisfy.  The key invariant (from dejevu):

  Every action the browser agent requests must be one of the named, validated
  operations in BrowserActionType. Raw JavaScript, raw selectors, raw coordinates,
  and shell commands are NEVER passed to any execution layer.

All validated actions flow through BrowserAction. The provider returns a
BrowserResult that the backend uses to build the final response.
"""
from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nia.browser_agent")


# ── Action allowlist (dejevu-inspired) ────────────────────────────────────────
# These are the ONLY operations a browser agent may request.
# Equivalent to dejevu's OPS tuple in types.py.

class BrowserActionType(str, enum.Enum):
    NAVIGATE   = "navigate"      # Load a URL
    CLICK      = "click"         # Click a labelled element
    TYPE       = "type"          # Enter text in a field
    SELECT     = "select"        # Choose a dropdown option
    SCROLL     = "scroll"        # Scroll the page
    WAIT       = "wait"          # Wait for content to load
    EXTRACT    = "extract"       # Extract visible text/data
    SCREENSHOT = "screenshot"    # Capture the current viewport
    DONE       = "done"          # Goal achieved — stop
    BLOCKED    = "blocked"       # Cannot make progress — stop


@dataclass
class BrowserAction:
    """
    A single browser operation requested by the model.
    Validated before execution — raw element indices, JS, or coordinates are NEVER here.
    """
    action_type: BrowserActionType
    url: Optional[str] = None             # for NAVIGATE
    label: Optional[str] = None           # for CLICK / TYPE / SELECT — human-readable label
    text: Optional[str] = None            # for TYPE — text to enter
    option: Optional[str] = None          # for SELECT — option label
    reason: Optional[str] = None          # for DONE / BLOCKED — why the agent stopped

    def validate(self) -> None:
        """Raise ValueError if this action is missing required fields."""
        if self.action_type == BrowserActionType.NAVIGATE and not self.url:
            raise ValueError("NAVIGATE action requires a url.")
        if self.action_type in (BrowserActionType.CLICK, BrowserActionType.TYPE,
                                BrowserActionType.SELECT) and not self.label:
            raise ValueError(f"{self.action_type.value.upper()} action requires a label.")
        if self.action_type == BrowserActionType.TYPE and self.text is None:
            raise ValueError("TYPE action requires text.")


@dataclass
class BrowserResult:
    """
    The final result of a browser agent session.
    status is 'done', 'blocked', or 'error'.
    """
    goal: str
    status: str                           # "done" | "blocked" | "error"
    url: Optional[str] = None
    extracted_text: Optional[str] = None
    screenshot_path: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    actions_taken: int = 0
    requests_made: int = 0


class BrowserProviderError(Exception):
    """Raised when the browser provider cannot complete a task."""


# ── Abstract base ──────────────────────────────────────────────────────────────

class BrowserAgentProvider(ABC):
    """
    Abstract browser agent backend.

    Implementations must honour the action allowlist: every browser action
    the model wants to take must pass through BrowserAction.validate() before
    it is executed. The implementation may NOT pass raw JS/selectors/coords to
    any execution layer.
    """

    @abstractmethod
    async def run(self, goal: str, start_url: Optional[str] = None) -> BrowserResult:
        """
        Run a browser session to achieve `goal`.

        Args:
          goal:      Natural-language description of what to accomplish.
          start_url: Optional starting URL; provider may choose a default.

        Returns:
          BrowserResult with status='done' on success, 'blocked'/'error' otherwise.

        Raises:
          BrowserProviderError on unrecoverable failure.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is configured and ready."""

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for health checks and logging."""


# ── Factory ────────────────────────────────────────────────────────────────────

def get_browser_agent_provider() -> BrowserAgentProvider:
    """
    Return the configured browser agent provider.
    Reads WEB_AGENT_PROVIDER from settings.
    """
    from ..core.config import settings
    name = (settings.WEB_AGENT_PROVIDER or "basic").lower().strip()

    if name == "dejevu":
        from .dejevu_stub import DejevuProvider
        return DejevuProvider()

    # Default: BasicProvider (httpx text fetch, no real browser)
    from .basic import BasicProvider
    return BasicProvider()
