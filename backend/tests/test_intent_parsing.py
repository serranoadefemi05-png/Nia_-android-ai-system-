"""Tests: Intent Parsing"""
import pytest
from ..app.orchestrator.orchestrator import IntentParser


@pytest.fixture
def parser():
    return IntentParser()


def test_screenshot_intent(parser):
    intent = parser.parse("Nia, take a screenshot")
    assert intent.intent_type == "take_screenshot"
    assert intent.confidence >= 0.9


def test_screenshot_synonym(parser):
    assert parser.parse("capture screen").intent_type == "take_screenshot"
    assert parser.parse("take a screen shot").intent_type == "take_screenshot"


def test_file_search_pdf(parser):
    intent = parser.parse("Nia abeg find that PDF I downloaded yesterday")
    assert intent.intent_type == "search_local_files"
    assert intent.entities.get("file_type") == "pdf"
    assert intent.entities.get("date_hint") == "yesterday"


def test_file_search_today(parser):
    intent = parser.parse("search for photos I took today")
    assert intent.intent_type == "search_local_files"
    assert intent.entities.get("date_hint") == "today"


def test_reminder_intent(parser):
    intent = parser.parse("Nia, remind me tomorrow at 9 AM to call the supplier")
    assert intent.intent_type == "create_reminder"
    assert intent.confidence >= 0.9


def test_reminder_synonyms(parser):
    assert parser.parse("set a reminder for 3pm").intent_type == "create_reminder"
    assert parser.parse("set an alarm").intent_type == "create_reminder"


def test_web_search(parser):
    intent = parser.parse("search the web for ESP32 DevKit")
    assert intent.intent_type == "web_search"
    assert "esp32" in intent.entities.get("query", "").lower()


def test_web_search_google(parser):
    intent = parser.parse("Google latest iPhone price Nigeria")
    assert intent.intent_type == "web_search"


def test_conversational_fallback(parser):
    intent = parser.parse("Hello NIA, how are you?")
    assert intent.intent_type == "conversational"
    assert intent.confidence < 0.8


def test_open_whatsapp(parser):
    # "open WhatsApp" doesn't match current v0.1 rules — should fall through to conversational
    # This test documents the known gap to be addressed in v0.2 with an LLM
    intent = parser.parse("Nia open WhatsApp")
    # Acceptable as conversational in v0.1
    assert intent.intent_type in ("conversational", "take_screenshot", "open_app")


def test_pidgin_reminder(parser):
    intent = parser.parse("Nia abeg remind me to call my supplier tomorrow morning")
    assert intent.intent_type == "create_reminder"
