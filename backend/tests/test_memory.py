"""
Tests for the NIA memory service and policy.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long!")

from app.memory.memory_service import MemoryService, MemoryType


@pytest.fixture()
def svc():
    return MemoryService()


def test_remember_and_recall(svc: MemoryService):
    svc.remember("user1", "preferred_language", "Yoruba")
    val = svc.recall("user1", "preferred_language")
    assert val == "Yoruba"


def test_upsert_updates_value(svc: MemoryService):
    svc.remember("user1", "city", "Lagos")
    svc.remember("user1", "city", "Abuja")
    assert svc.recall("user1", "city") == "Abuja"


def test_recall_missing_key_returns_none(svc: MemoryService):
    assert svc.recall("user1", "nonexistent_key_xyz") is None


def test_forget_single_entry(svc: MemoryService):
    entry = svc.remember("user1", "fact1", "some fact")
    deleted = svc.forget("user1", entry.id)
    assert deleted
    assert svc.recall("user1", "fact1") is None


def test_forget_all(svc: MemoryService):
    svc.remember("user1", "k1", "v1")
    svc.remember("user1", "k2", "v2")
    count = svc.forget_all("user1")
    assert count == 2
    assert svc.list_memory("user1") == []


def test_sensitive_key_blocked(svc: MemoryService):
    for key in ["password", "pin", "secret", "private_key", "seed", "passphrase"]:
        with pytest.raises(PermissionError):
            svc.remember("user1", key, "value123")


def test_value_too_large_blocked(svc: MemoryService):
    with pytest.raises(ValueError, match="too large"):
        svc.remember("user1", "bigkey", "x" * 11_000)


def test_list_by_type(svc: MemoryService):
    svc.remember("user1", "fav_food", "jollof", memory_type=MemoryType.PREFERENCE)
    svc.remember("user1", "last_task", "screenshot", memory_type=MemoryType.TASK_HISTORY)
    prefs = svc.list_memory("user1", memory_type=MemoryType.PREFERENCE)
    assert all(e.memory_type == MemoryType.PREFERENCE for e in prefs)
    history = svc.list_memory("user1", memory_type=MemoryType.TASK_HISTORY)
    assert all(e.memory_type == MemoryType.TASK_HISTORY for e in history)


def test_users_isolated(svc: MemoryService):
    svc.remember("alice", "name", "Alice")
    svc.remember("bob", "name", "Bob")
    assert svc.recall("alice", "name") == "Alice"
    assert svc.recall("bob", "name") == "Bob"
    svc.forget_all("alice")
    assert svc.recall("alice", "name") is None
    assert svc.recall("bob", "name") == "Bob"  # Bob unaffected
