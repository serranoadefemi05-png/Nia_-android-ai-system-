"""
Tests for NiaLLMResponse schema validation.

Ensures the Pydantic schema correctly accepts valid model output and rejects
malformed, missing, or injection-containing output.
"""
from __future__ import annotations

import json
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long!")

from pydantic import ValidationError
from app.llm.response_schema import NiaLLMResponse, NiaToolCall, ALLOWED_TOOL_IDS


# ── Valid responses ────────────────────────────────────────────────────────

def test_valid_conversational():
    r = NiaLLMResponse(
        response="The capital of Nigeria is Abuja.",
        intent="conversational",
        tool_call=None,
    )
    assert r.intent == "conversational"
    assert r.tool_call is None


def test_valid_tool_call():
    r = NiaLLMResponse(
        response="Taking a screenshot now.",
        intent="take_screenshot",
        tool_call=NiaToolCall(
            tool_id="take_screenshot",
            arguments={},
            requires_confirmation=False,
        ),
    )
    assert r.tool_call.tool_id == "take_screenshot"


def test_valid_tool_with_args():
    r = NiaLLMResponse(
        response="Reminder set.",
        intent="create_reminder",
        tool_call=NiaToolCall(
            tool_id="create_reminder",
            arguments={"title": "Call John", "hour": 8, "minute": 0},
            requires_confirmation=False,
        ),
    )
    assert r.tool_call.arguments["hour"] == 8


# ── Invalid tool IDs ───────────────────────────────────────────────────────

def test_unknown_tool_id_rejected():
    """Model cannot request a tool not in the allowlist."""
    with pytest.raises(ValidationError) as exc_info:
        NiaToolCall(
            tool_id="delete_all_user_data",   # not registered
            arguments={},
        )
    assert "Allowed" in str(exc_info.value) or "unknown" in str(exc_info.value).lower()


@pytest.mark.parametrize("tool_id", sorted(ALLOWED_TOOL_IDS))
def test_all_allowed_tools_accepted(tool_id):
    tc = NiaToolCall(tool_id=tool_id, arguments={})
    assert tc.tool_id == tool_id


# ── Invalid intents ────────────────────────────────────────────────────────

def test_intent_with_spaces_rejected():
    with pytest.raises(ValidationError):
        NiaLLMResponse(
            response="Hello",
            intent="open the app",   # spaces not allowed
            tool_call=None,
        )


def test_intent_with_uppercase_rejected():
    with pytest.raises(ValidationError):
        NiaLLMResponse(
            response="Hello",
            intent="Conversational",  # must be lowercase
            tool_call=None,
        )


# ── Empty / blank responses ────────────────────────────────────────────────

def test_blank_response_rejected():
    with pytest.raises(ValidationError):
        NiaLLMResponse(response="   ", intent="conversational", tool_call=None)


def test_empty_response_rejected():
    with pytest.raises(ValidationError):
        NiaLLMResponse(response="", intent="conversational", tool_call=None)


# ── Oversized arguments ────────────────────────────────────────────────────

def test_oversized_arguments_rejected():
    big_args = {"data": "x" * 9000}
    with pytest.raises(ValidationError):
        NiaToolCall(tool_id="web_search", arguments=big_args)


# ── JSON round-trip ────────────────────────────────────────────────────────

def test_json_roundtrip():
    r = NiaLLMResponse(
        response="Abuja is the capital.",
        intent="conversational",
        tool_call=None,
    )
    data = json.loads(r.model_dump_json())
    r2 = NiaLLMResponse.model_validate(data)
    assert r2.response == r.response
    assert r2.intent == r.intent
