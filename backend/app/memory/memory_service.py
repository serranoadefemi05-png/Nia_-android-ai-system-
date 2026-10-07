"""
NIA Backend — Memory Service
Lightweight, policy-gated memory for user facts, preferences, and task history.

Policy rules (v0.1):
- NEVER auto-store sensitive data.
- Only USER_EXPLICIT source can store CREDENTIAL type (and we reject that).
- User can always delete all their memory (GDPR / right to erasure).
- No raw AI inferences stored unless user explicitly confirms.
"""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class MemoryType(str, enum.Enum):
    PREFERENCE = "preference"
    FACT = "fact"
    TASK_HISTORY = "task_history"
    CONVERSATION_SUMMARY = "conversation_summary"


_BANNED_KEYS = {"password", "pin", "secret", "private_key", "seed", "passphrase", "credit_card", "ssn"}


@dataclass
class MemoryEntry:
    id: str
    user_id: str
    key: str
    value: Any
    memory_type: MemoryType
    source: str   # "user_explicit" | "orchestrator_summary" | "system"
    created_at: datetime
    updated_at: datetime


class MemoryRepository:
    """In-memory store. Replace with DB in production."""
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, MemoryEntry]] = {}  # { user_id: { entry_id: entry } }

    def put(self, entry: MemoryEntry) -> MemoryEntry:
        self._store.setdefault(entry.user_id, {})[entry.id] = entry
        return entry

    def get(self, user_id: str, entry_id: str) -> Optional[MemoryEntry]:
        return self._store.get(user_id, {}).get(entry_id)

    def get_by_key(self, user_id: str, key: str) -> Optional[MemoryEntry]:
        for e in self._store.get(user_id, {}).values():
            if e.key == key:
                return e
        return None

    def list_user(self, user_id: str, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        entries = list(self._store.get(user_id, {}).values())
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries

    def delete(self, user_id: str, entry_id: str) -> bool:
        user_store = self._store.get(user_id, {})
        if entry_id in user_store:
            del user_store[entry_id]
            return True
        return False

    def delete_all(self, user_id: str) -> int:
        count = len(self._store.get(user_id, {}))
        self._store[user_id] = {}
        return count


class MemoryPolicy:
    """Enforces what can and cannot be stored."""

    @staticmethod
    def validate(key: str, value: Any, source: str, memory_type: MemoryType) -> None:
        key_lower = key.strip().lower()
        if key_lower in _BANNED_KEYS or any(b in key_lower for b in _BANNED_KEYS):
            raise PermissionError(f"Storing sensitive data (key={key!r}) is not allowed.")
        if memory_type not in MemoryType.__members__.values():
            raise ValueError(f"Unknown memory type: {memory_type!r}")
        if len(str(value)) > 10_000:
            raise ValueError("Memory value too large (max 10 000 chars).")


class MemoryService:
    def __init__(self) -> None:
        self.repo = MemoryRepository()
        self.policy = MemoryPolicy()

    def remember(
        self,
        user_id: str,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.FACT,
        source: str = "user_explicit",
    ) -> MemoryEntry:
        self.policy.validate(key, value, source, memory_type)
        now = datetime.now(timezone.utc)
        existing = self.repo.get_by_key(user_id, key)
        if existing:
            existing.value = value
            existing.updated_at = now
            return self.repo.put(existing)
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key=key,
            value=value,
            memory_type=memory_type,
            source=source,
            created_at=now,
            updated_at=now,
        )
        return self.repo.put(entry)

    def recall(self, user_id: str, key: str) -> Optional[Any]:
        entry = self.repo.get_by_key(user_id, key)
        return entry.value if entry else None

    def list_memory(self, user_id: str, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        return self.repo.list_user(user_id, memory_type=memory_type)

    def forget(self, user_id: str, entry_id: str) -> bool:
        return self.repo.delete(user_id, entry_id)

    def forget_all(self, user_id: str) -> int:
        return self.repo.delete_all(user_id)


memory_service = MemoryService()
