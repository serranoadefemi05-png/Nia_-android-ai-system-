"""
NIA Backend — Task History / Observability
Every executed task produces an ExecutionRecord stored here.
Logs: task ID, timestamp, intent, selected tool, parameters (secrets excluded),
permission state, confirmation state, execution result, verification result,
failure reason if any.

NEVER log: passwords, API keys, private keys, authentication tokens,
or sensitive personal content.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Keys whose values must never appear in logs
_REDACT_KEYS = frozenset({
    "password", "pin", "secret", "api_key", "token", "auth",
    "private_key", "seed_phrase", "credit_card", "cvv",
    "authorization", "bearer",
})


def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of params with sensitive values replaced by a redaction marker."""
    out = {}
    for k, v in params.items():
        if any(bad in k.lower() for bad in _REDACT_KEYS):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _redact(v)
        else:
            out[k] = v
    return out


class TaskOutcome(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PERMISSION_DENIED = "permission_denied"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


@dataclass
class ExecutionRecord:
    task_id: str
    timestamp: datetime
    user_id: str
    intent: str
    selected_tool: Optional[str]
    parameters: Dict[str, Any]          # Already redacted — no secrets
    permission_state: str               # "granted" | "denied" | "partial"
    confirmation_state: str             # "not_required" | "confirmed" | "pending" | "cancelled"
    outcome: TaskOutcome
    execution_result: Optional[Dict[str, Any]]
    verified: bool
    failure_reason: Optional[str]
    duration_ms: Optional[int] = None
    raw_text: str = ""


class TaskHistoryStore:
    """
    In-memory store for execution records.
    Replace with a persistent DB (SQLite/Postgres) for production.
    Scoped per user_id.
    """

    def __init__(self) -> None:
        # { user_id: [ExecutionRecord, ...] } — newest first
        self._records: Dict[str, List[ExecutionRecord]] = {}
        self._max_per_user = 500

    def record(self, rec: ExecutionRecord) -> None:
        user_recs = self._records.setdefault(rec.user_id, [])
        user_recs.insert(0, rec)
        if len(user_recs) > self._max_per_user:
            del user_recs[self._max_per_user:]
        logger.info(
            "task=%s user=%s intent=%s tool=%s outcome=%s",
            rec.task_id, rec.user_id, rec.intent,
            rec.selected_tool, rec.outcome.value,
        )

    def get(self, user_id: str, limit: int = 50, offset: int = 0) -> List[ExecutionRecord]:
        recs = self._records.get(user_id, [])
        return recs[offset: offset + limit]

    def get_by_id(self, user_id: str, task_id: str) -> Optional[ExecutionRecord]:
        for r in self._records.get(user_id, []):
            if r.task_id == task_id:
                return r
        return None

    def clear(self, user_id: str) -> int:
        count = len(self._records.get(user_id, []))
        self._records[user_id] = []
        return count


task_history = TaskHistoryStore()


def new_task_id() -> str:
    """Generate a short, URL-safe, opaque task ID."""
    return "task_" + secrets.token_urlsafe(8)


def build_record(
    *,
    task_id: str,
    user_id: str,
    raw_text: str,
    intent: str,
    selected_tool: Optional[str],
    parameters: Dict[str, Any],
    permission_state: str,
    confirmation_state: str,
    outcome: TaskOutcome,
    execution_result: Optional[Dict[str, Any]],
    verified: bool,
    failure_reason: Optional[str],
    duration_ms: Optional[int] = None,
) -> ExecutionRecord:
    return ExecutionRecord(
        task_id=task_id,
        timestamp=datetime.now(timezone.utc),
        user_id=user_id,
        intent=intent,
        selected_tool=selected_tool,
        parameters=_redact(parameters),
        permission_state=permission_state,
        confirmation_state=confirmation_state,
        outcome=outcome,
        execution_result=execution_result,
        verified=verified,
        failure_reason=failure_reason,
        duration_ms=duration_ms,
        raw_text=raw_text,
    )
