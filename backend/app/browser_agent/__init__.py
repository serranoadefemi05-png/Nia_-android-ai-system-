"""
NIA Browser Agent package.

Inspired by: dejevu's Loop/Policy/Browser architecture (dejevu/agent.py, policy.py)

Provides a BrowserAgentProvider abstraction for delegating web browsing tasks
to a safe, validated browser agent.

Design principles (directly from dejevu):
  - "Model output never reaches the page as code."
  - Every browser action must be one of a named, allowlisted operation set.
  - No raw JavaScript, no CSS selectors, no coordinates, no shell commands
    may pass from the model to the execution layer.
  - Each action is validated before execution.
  - The agent reports DONE or BLOCKED explicitly — it never silently succeeds.

Current providers:
  BasicProvider    — httpx GET + text extraction; no real browser (v0.1)
  DejevuProvider   — future: CDP-based browser agent inspired by dejevu; stub only

The Android app NEVER receives raw browser actions. The backend executes
the browser session entirely server-side and returns structured results.
"""
from .provider import (
    BrowserAgentProvider,
    BrowserAction,
    BrowserResult,
    BrowserActionType,
    BrowserProviderError,
    get_browser_agent_provider,
)

__all__ = [
    "BrowserAgentProvider",
    "BrowserAction",
    "BrowserResult",
    "BrowserActionType",
    "BrowserProviderError",
    "get_browser_agent_provider",
]
