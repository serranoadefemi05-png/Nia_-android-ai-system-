"""
NIA Backend — LLM Response Schema

Every LLM response is validated through this schema before the orchestrator
acts on it. A malformed model output raises a ValidationError — it is never
silently accepted and never fabricated.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# Allowlist of tool IDs the model is permitted to request.
# This list must stay in sync with ToolRegistry registrations.
ALLOWED_TOOL_IDS: frozenset[str] = frozenset({
    "take_screenshot",
    "search_local_files",
    "create_reminder",
    "web_search",
    "open_app",
    "read_notification",
    "send_message",
    "delete_file",
    "make_payment",
})


class NiaToolCall(BaseModel):
    """Structured tool invocation requested by the model."""

    tool_id: str = Field(..., description="ID of the registered tool to invoke.")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool executor.",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="True if the model believes this action needs user approval.",
    )

    @field_validator("tool_id")
    @classmethod
    def tool_id_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_TOOL_IDS:
            raise ValueError(
                f"Model requested unknown tool {v!r}. "
                f"Allowed: {sorted(ALLOWED_TOOL_IDS)}"
            )
        return v

    @field_validator("arguments")
    @classmethod
    def arguments_must_be_dict(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        # Shallow size guard — prevents absurdly large argument payloads
        raw = str(v)
        if len(raw) > 8192:
            raise ValueError("Tool arguments payload is too large (max 8192 chars).")
        return v


class NiaLLMResponse(BaseModel):
    """
    Canonical response contract that every LLM backend must return.

    The model must reply with a JSON object matching this schema.
    Any deviation causes a ValidationError — the orchestrator then
    returns a safe error to the user instead of proceeding.
    """

    response: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="Natural-language reply to speak/display to the user.",
    )
    intent: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Short intent label e.g. 'conversational', 'take_screenshot'.",
    )
    tool_call: Optional[NiaToolCall] = Field(
        default=None,
        description="Set only when the model wants to invoke a registered tool.",
    )
    reasoning: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Optional chain-of-thought (never shown to end users).",
    )

    @field_validator("intent")
    @classmethod
    def intent_no_special_chars(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(
                f"Intent must be lowercase alphanumeric + underscores, got {v!r}."
            )
        return v

    @field_validator("response")
    @classmethod
    def response_not_empty_after_strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Response must not be blank after stripping whitespace.")
        return v.strip()
