"""
NIA Browser Agent — Dejevu-Inspired Provider (Stub)

This is a STUB for a future CDP-based browser agent inspired by the dejevu project
(https://github.com/idovmamane/dejevu).

Design intent (NOT YET IMPLEMENTED):

  dejevu's architecture:
    Loop (observe → decide → guard → act → settle)
      Tab (CDP session over a Chrome process)
      LLMPolicy (model returns one JSON decision per step)
      validate(decision, page)  ← action validated before execution
      tab.act(action)           ← validated action executed

  NIA DejevuProvider will mirror this:
    NiaBrowserLoop (observe → plan → validate → act → observe)
      AndroidWebView or server-side Chrome via CDP
      Planner (NIA's existing LLM provider)
      BrowserAction.validate()  ← action validated before execution
      BrowserTab.act(action)    ← validated action executed

  Key dejevu invariants preserved:
    - Model output NEVER reaches the browser as raw code
    - Every action is one of the named BrowserActionType operations
    - DONE / BLOCKED are the only terminal states
    - Max 40 actions / 80 LLM requests per session (dejevu defaults)
    - Retry on JSON parse failure (AnswerError in dejevu)
    - Loop detection: same action 4 times in 6 steps → BLOCKED

  What makes this different from copying dejevu:
    - Uses NIA's LLMProvider instead of dejevu's LLMPolicy directly
    - No macOS assumption; targets a server-side Chrome or a proxy CDP endpoint
    - Actions return to NIA backend before any Android execution
    - All web content is wrapped with wrap_external_content() before LLM sees it

CONFIGURATION:
  WEB_AGENT_PROVIDER=dejevu
  DEJEVU_CDP_URL=http://localhost:9222  (a remote Chrome instance)
  DEJEVU_MAX_ACTIONS=40
  DEJEVU_MAX_REQUESTS=80

This stub raises NotImplementedError on run() until the full implementation
is built in a future version.
"""
from __future__ import annotations

import logging
from typing import Optional

from .provider import BrowserAgentProvider, BrowserResult, BrowserProviderError

logger = logging.getLogger("nia.browser_agent.dejevu")


class DejevuProvider(BrowserAgentProvider):
    """
    Future: CDP-based browser agent following the dejevu observe→decide→act pattern.

    Currently a stub. Returns is_available()=False so the orchestrator
    falls back to BasicProvider gracefully.
    """

    def is_available(self) -> bool:
        # Not yet implemented
        return False

    def provider_name(self) -> str:
        return "dejevu"

    async def run(
        self,
        goal: str,
        start_url: Optional[str] = None,
    ) -> BrowserResult:
        logger.warning(
            "DEJEVU_STUB DejevuProvider.run() called but provider is not yet implemented. "
            "Set WEB_AGENT_PROVIDER=basic to use the BasicProvider instead."
        )
        raise BrowserProviderError(
            "The dejevu browser agent provider is not yet implemented. "
            "Configure WEB_AGENT_PROVIDER=basic in your .env file."
        )
