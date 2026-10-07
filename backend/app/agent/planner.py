"""
NIA Agent — Planner

Inspired by: OpenYabby agent-task-processor.js + dejevu policy.py

The planner receives a sanitized user utterance (already through security.py)
and produces a PlannerResult:
  - intent label
  - optional tool request (id + arguments + confirmation flag)
  - natural-language response (may be empty if a tool is being dispatched)
  - reasoning (never shown to user; used for loop detection / hallucination guard)

The planner calls the LLM provider ONCE. For multi-step tasks, the orchestrator
calls the planner again with the tool result added to history.

Loop detection (inspired by OpenYabby's retry-detector.js):
  If the same tool is requested twice with the same arguments in one session,
  the planner raises PlannerLoopError instead of executing the third time.

Hallucination guard (inspired by OpenYabby's hallucination-detector.js):
  The planner NEVER trusts the model's claim that a tool succeeded.
  The observer (observer.py) validates the actual Android tool result separately.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..llm.provider import (
    LLMNotConfiguredError,
    LLMResponseError,
    LLMTimeoutError,
    get_llm_provider,
)
from ..llm.response_schema import NiaLLMResponse, NiaToolCall

logger = logging.getLogger("nia.planner")

# Maximum times the same (tool_id, args_hash) pair may appear in one session
# before PlannerLoopError is raised.  Inspired by OpenYabby retry-detector.js.
MAX_SAME_TOOL_CALLS = 3


class PlannerLoopError(RuntimeError):
    """Raised when the planner detects a suspected tool-call loop."""


@dataclass
class PlannerResult:
    """The planner's output. Mirrors NiaLLMResponse but is a first-class type."""
    intent: str
    response: str
    tool_call: Optional[NiaToolCall] = None
    reasoning: Optional[str] = None
    provider: str = ""
    model: str = ""

    @property
    def needs_tool(self) -> bool:
        return self.tool_call is not None

    @property
    def is_conversational(self) -> bool:
        return self.tool_call is None


class Planner:
    """
    Classifies intent and selects a tool (or decides to respond conversationally).

    Instantiate once per conversation session; the call_log tracks tool-call history
    for loop detection. For stateless single-shot use (e.g. simple REST endpoint),
    create a fresh Planner() per request.
    """

    def __init__(self) -> None:
        # call_log: { args_hash -> count } for loop detection
        self._call_log: Dict[str, int] = {}

    async def plan(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> PlannerResult:
        """
        Call the LLM and return a validated PlannerResult.

        Raises:
          LLMNotConfiguredError   — provider has no credentials
          LLMResponseError        — model returned unparseable/invalid output
          LLMTimeoutError         — request timed out
          PlannerLoopError        — same tool called too many times (loop guard)
        """
        provider = get_llm_provider()

        if not provider.is_configured():
            raise LLMNotConfiguredError(
                "NIA's AI provider is not configured yet. "
                "Set LLM_PROVIDER and the matching API key in the backend .env file."
            )

        # Ask the LLM — it returns a fully validated NiaLLMResponse
        llm_response: NiaLLMResponse = await provider.generate_structured(
            user_message=user_message,
            conversation_history=conversation_history,
        )

        # Loop detection: track (tool_id, args_hash) frequency
        if llm_response.tool_call is not None:
            call_key = _tool_call_key(llm_response.tool_call)
            self._call_log[call_key] = self._call_log.get(call_key, 0) + 1
            if self._call_log[call_key] > MAX_SAME_TOOL_CALLS:
                logger.warning(
                    "LOOP_DETECTED tool=%s key=%s count=%d",
                    llm_response.tool_call.tool_id,
                    call_key[:16],
                    self._call_log[call_key],
                )
                raise PlannerLoopError(
                    f"Planner called tool '{llm_response.tool_call.tool_id}' with the "
                    f"same arguments {self._call_log[call_key]} times — possible loop."
                )

        logger.info(
            "PLAN provider=%s model=%s intent=%s tool=%s",
            provider.provider_name(),
            provider.model_name(),
            llm_response.intent,
            llm_response.tool_call.tool_id if llm_response.tool_call else "none",
        )

        return PlannerResult(
            intent=llm_response.intent,
            response=llm_response.response,
            tool_call=llm_response.tool_call,
            reasoning=llm_response.reasoning,
            provider=provider.provider_name(),
            model=provider.model_name(),
        )

    def reset_loop_state(self) -> None:
        """Clear loop-detection state between independent sessions."""
        self._call_log.clear()


def _tool_call_key(tool_call: NiaToolCall) -> str:
    """Stable hash of (tool_id, sorted_args) for loop detection."""
    args_str = json.dumps(tool_call.arguments, sort_keys=True, ensure_ascii=False)
    raw = f"{tool_call.tool_id}::{args_str}"
    return hashlib.sha256(raw.encode()).hexdigest()
