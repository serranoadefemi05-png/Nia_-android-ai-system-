"""Tests: Permission Checking"""
import pytest
from ..app.orchestrator.orchestrator import (
    IntentParser, Planner, PermissionChecker
)


@pytest.fixture
def pipeline():
    return IntentParser(), Planner(), PermissionChecker()


def test_screenshot_requires_media_projection(pipeline):
    parser, planner, checker = pipeline
    intent = parser.parse("take a screenshot")
    plan = planner.plan(intent)
    missing = checker.check(plan, granted_permissions=[])
    assert "MEDIA_PROJECTION" in missing


def test_screenshot_passes_with_permission(pipeline):
    parser, planner, checker = pipeline
    intent = parser.parse("take a screenshot")
    plan = planner.plan(intent)
    missing = checker.check(plan, granted_permissions=["MEDIA_PROJECTION"])
    assert missing == []


def test_file_search_requires_storage(pipeline):
    parser, planner, checker = pipeline
    intent = parser.parse("find that PDF I downloaded")
    plan = planner.plan(intent)
    missing = checker.check(plan, granted_permissions=[])
    assert "READ_EXTERNAL_STORAGE" in missing


def test_web_search_needs_no_permissions(pipeline):
    parser, planner, checker = pipeline
    intent = parser.parse("search the web for Python tutorials")
    plan = planner.plan(intent)
    missing = checker.check(plan, granted_permissions=[])
    assert missing == []


def test_reminder_requires_alarm_permission(pipeline):
    parser, planner, checker = pipeline
    intent = parser.parse("remind me tomorrow at 9am to call")
    plan = planner.plan(intent)
    missing = checker.check(plan, granted_permissions=[])
    assert "SET_ALARM" in missing or "SCHEDULE_EXACT_ALARM" in missing


def test_unknown_tool_flags_as_missing(pipeline):
    _, _, checker = pipeline
    from ..app.orchestrator.orchestrator import Plan, Intent, PlanStep
    from ..app.tools.registry import ConfirmationLevel
    plan = Plan(
        intent=Intent(raw_text="test", intent_type="take_screenshot"),
        steps=[PlanStep(
            tool_id="nonexistent_tool",
            parameters={},
            description="test",
            confirmation_level=ConfirmationLevel.GREEN,
        )],
    )
    missing = checker.check(plan, granted_permissions=[])
    assert any("UNKNOWN_TOOL" in m for m in missing)
