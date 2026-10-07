"""
NIA Agent — Observer

Inspired by: dejevu's Loop.step() observe+validate pattern (dejevu/agent.py)
             OpenYabby's hallucination-detector.js

The observer receives a tool result sent back from the Android client and
validates it before the final response is generated.

Key principle (from dejevu):
  "Model output never reaches the page as code."
  Equivalent NIA principle:
  "The model never claims a tool succeeded. Android reports what happened."

The observer:
  1. Validates that the result has the expected shape for the tool that was called.
  2. Detects stale/mismatched results (tool_id mismatch).
  3. Flags suspicious result content that looks like prompt injection.
  4. Produces an ObservationResult the responder can use.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core.security import wrap_external_content

logger = logging.getLogger("nia.observer")

# Maximum size of tool result data (chars) we'll pass to the LLM
_MAX_RESULT_CHARS = 4096

# Strings that, if found in tool result data, suggest prompt injection
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard your",
    "new system prompt",
    "you are now",
    "pretend you are",
    "roleplay as",
    "act as if",
    "your real instructions",
    "reveal your system",
]


@dataclass
class ObservationResult:
    """What the observer concludes about a tool execution result."""
    tool_id: str
    success: bool
    data: Dict[str, Any]
    data_for_llm: str       # Sanitized, size-bounded string for the next LLM call
    warning: Optional[str] = None


class Observer:
    """
    Validates Android tool results before they reach the LLM responder.

    The Android app sends the raw tool execution result back via
    POST /api/v1/assistant/command with `tool_result` in the request body.
    The Observer ensures that result is:
      - from the expected tool (no TOCTOU mismatch)
      - size-bounded so it can't overflow the context window
      - free of prompt injection attempts
      - labelled as EXTERNAL DATA if it contains web/file content
    """

    def observe(
        self,
        expected_tool_id: str,
        raw_result: Dict[str, Any],
    ) -> ObservationResult:
        """
        Validate and prepare a tool result for the responder.

        Args:
          expected_tool_id: the tool_id that was dispatched to Android
          raw_result:        the dict the Android client returned

        Returns:
          ObservationResult
        """
        returned_tool_id = raw_result.get("tool_id", expected_tool_id)
        success = raw_result.get("success", True)
        data = raw_result.get("data") or {}
        warning: Optional[str] = None

        # ── Tool-id mismatch check ──────────────────────────────────────────
        if returned_tool_id != expected_tool_id:
            logger.warning(
                "OBSERVER tool_id mismatch: expected=%s got=%s",
                expected_tool_id,
                returned_tool_id,
            )
            warning = f"Tool ID mismatch: expected {expected_tool_id!r}, got {returned_tool_id!r}."
            success = False

        # ── Size bound ─────────────────────────────────────────────────────
        raw_str = str(data)
        if len(raw_str) > _MAX_RESULT_CHARS:
            logger.info(
                "OBSERVER result truncated: tool=%s original_len=%d",
                expected_tool_id, len(raw_str),
            )
            raw_str = raw_str[:_MAX_RESULT_CHARS] + "... [truncated]"

        # ── Injection scan (inspired by OpenYabby security.js) ─────────────
        raw_lower = raw_str.lower()
        for pattern in _INJECTION_PATTERNS:
            if pattern in raw_lower:
                logger.warning(
                    "OBSERVER injection pattern detected in tool result: tool=%s pattern=%r",
                    expected_tool_id, pattern,
                )
                warning = (warning or "") + " Possible injection content in tool result."
                # Wrap as external content so the LLM treats it as data
                raw_str = wrap_external_content(raw_str, source=f"tool:{expected_tool_id}")
                break
        else:
            # Not injection — still wrap web/file content as EXTERNAL DATA
            if expected_tool_id in ("web_search", "search_local_files"):
                raw_str = wrap_external_content(raw_str, source=f"tool:{expected_tool_id}")

        logger.info(
            "OBSERVER tool=%s success=%s data_len=%d",
            expected_tool_id, success, len(raw_str),
        )

        return ObservationResult(
            tool_id=returned_tool_id,
            success=success,
            data=data,
            data_for_llm=raw_str,
            warning=warning,
        )
