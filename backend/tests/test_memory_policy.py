"""Tests: Memory Policy"""
import pytest
from ..app.memory.memory_service import MemoryService, MemoryPolicy, MemoryType


@pytest.fixture
def svc():
    return MemoryService()


FORBIDDEN_KEYS = [
    "password", "my_password", "user_password",
    "pin", "my_pin",
    "api_key", "openai_api_key",
    "private_key", "wallet_private_key",
    "seed_phrase",
    "credit_card",
]


@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
def test_forbidden_key_blocked(svc, key):
    with pytest.raises((ValueError, PermissionError)):
        svc.remember("user_1", key, "some_value")


def test_normal_fact_stored(svc):
    entry = svc.remember("user_1", "supplier_name", "Chukwu Electronics")
    assert entry.key == "supplier_name"
    assert entry.value == "Chukwu Electronics"


def test_recall_returns_entries(svc):
    svc.remember("user_2", "favorite_language", "Yoruba")
    entries = svc.recall("user_2", "favorite_language")
    assert len(entries) == 1
    assert entries[0].value == "Yoruba"


def test_forget_removes_entry(svc):
    entry = svc.remember("user_3", "my_contact", "Emeka: 0801234567")
    deleted = svc.forget("user_3", entry.id)
    assert deleted
    assert svc.recall("user_3", "my_contact") == []


def test_forget_all_clears_memory(svc):
    svc.remember("user_4", "fact_a", "value_a")
    svc.remember("user_4", "fact_b", "value_b")
    count = svc.forget_all("user_4")
    assert count == 2
    assert svc.list_memory("user_4") == []


def test_value_too_large_blocked(svc):
    with pytest.raises(ValueError):
        svc.remember("user_5", "big_fact", "x" * 10_001)


def test_auto_store_forbidden_for_sensitive_keys():
    assert not MemoryPolicy.can_auto_store("password", MemoryType.TASK_HISTORY)
    assert not MemoryPolicy.can_auto_store("api_key", MemoryType.CONVERSATION_SUMMARY)


def test_auto_store_allowed_for_task_history():
    assert MemoryPolicy.can_auto_store("task_summary", MemoryType.TASK_HISTORY)
