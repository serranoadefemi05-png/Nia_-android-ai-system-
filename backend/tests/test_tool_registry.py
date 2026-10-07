"""
Tests for the NIA tool registry.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long!")

from app.tools.registry import registry, ConfirmationLevel, RiskLevel, Tool


def test_all_mvp_tools_registered():
    tool_ids = {t.id for t in registry.list_tools()}
    assert "take_screenshot" in tool_ids
    assert "search_local_files" in tool_ids
    assert "create_reminder" in tool_ids
    assert "web_search" in tool_ids
    assert "open_app" in tool_ids
    assert "send_message" in tool_ids
    assert "delete_file" in tool_ids
    assert "make_payment" in tool_ids


def test_green_tools_do_not_require_confirmation():
    for tool in registry.list_tools():
        if tool.risk_level == RiskLevel.LOW:
            assert tool.confirmation_level == ConfirmationLevel.GREEN, \
                f"LOW risk tool {tool.id!r} should be GREEN"


def test_high_critical_tools_require_confirmation():
    for tool in registry.list_tools():
        if tool.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            assert tool.confirmation_level in (ConfirmationLevel.YELLOW, ConfirmationLevel.RED), \
                f"HIGH/CRITICAL tool {tool.id!r} must require confirmation"


def test_make_payment_is_red():
    t = registry.get("make_payment")
    assert t.risk_level == RiskLevel.CRITICAL
    assert t.confirmation_level == ConfirmationLevel.RED


def test_screenshot_is_green():
    t = registry.get("take_screenshot")
    assert t.risk_level == RiskLevel.LOW
    assert t.confirmation_level == ConfirmationLevel.GREEN
    assert not registry.requires_confirmation("take_screenshot")


def test_send_message_requires_confirmation():
    assert registry.requires_confirmation("send_message")


def test_unknown_tool_raises():
    with pytest.raises(KeyError):
        registry.get("nonexistent_tool_xyz")


def test_llm_descriptions_are_dicts():
    descs = registry.to_llm_descriptions()
    assert len(descs) > 0
    for d in descs:
        assert "id" in d
        assert "description" in d
        assert "risk_level" in d
        assert "confirmation_level" in d
