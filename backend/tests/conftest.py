"""
NIA test configuration.

Patches the LLM provider singleton so tests never make real HTTP calls.
The mock provider returns a configurable NiaLLMResponse that tests can
override per-scenario.
"""
from __future__ import annotations

import os
import sys
import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

# Make sure the backend package is importable from the tests/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Provide the minimum required env vars so Settings() doesn't fail
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long!")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-never-used-in-tests")


from app.llm.provider import LLMProvider, reset_provider_for_testing
from app.llm.response_schema import NiaLLMResponse, NiaToolCall


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM provider for testing.
    Responses are controlled via MockLLMProvider.set_response().
    """

    def __init__(self) -> None:
        self._response: Optional[NiaLLMResponse] = None
        self._raise: Optional[Exception] = None
        self.call_count = 0
        self.last_message: Optional[str] = None

    def set_response(self, response: NiaLLMResponse) -> None:
        self._response = response
        self._raise = None

    def set_error(self, exc: Exception) -> None:
        self._raise = exc
        self._response = None

    def is_configured(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "mock"

    def model_name(self) -> str:
        return "mock-model"

    async def generate_structured(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> NiaLLMResponse:
        self.call_count += 1
        self.last_message = user_message
        if self._raise is not None:
            raise self._raise
        if self._response is not None:
            return self._response
        # Default: conversational reply matching the input
        return NiaLLMResponse(
            response=f"Mock response to: {user_message}",
            intent="conversational",
            tool_call=None,
        )


@pytest.fixture(autouse=True)
def mock_llm_provider():
    """
    Auto-used fixture: replaces the LLM provider singleton with MockLLMProvider
    for every test. Resets it after the test.
    """
    reset_provider_for_testing()
    provider = MockLLMProvider()

    import app.llm.provider as llm_mod
    original = llm_mod._provider_instance
    llm_mod._provider_instance = provider

    yield provider

    llm_mod._provider_instance = original
    reset_provider_for_testing()
