"""
NIA Backend — API Routes
All endpoints the Android app and web UI connect to.

POST /api/v1/command       — Main voice command processing endpoint
GET  /api/v1/tools         — List available tools
GET  /api/v1/history       — Task execution history for the user
GET  /api/v1/memory        — List NIA's memory entries for the user
DELETE /api/v1/memory/{id} — Delete a memory entry
DELETE /api/v1/memory      — Delete ALL memory for the user
GET  /api/v1/health        — Health check
GET  /api/v1/arc/status    — Arc integration status
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..orchestrator.orchestrator import orchestrator
from ..tools.registry import registry
from ..memory.memory_service import memory_service, MemoryType
from ..arc.arc_service import arc_service
from ..task_history import (
    TaskOutcome, build_record, new_task_id, task_history,
)
from ..core.security import sanitize_user_input

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Auth helper (simple device-token check for v0.1)
# ---------------------------------------------------------------------------

# In v0.1 any non-empty X-Device-Id header identifies the user.
# Replace with real JWT authentication in production.
def get_user_id(x_device_id: Optional[str] = Header(default=None)) -> str:
    if not x_device_id:
        return "anonymous"
    return x_device_id[:64]  # Truncate to prevent abuse


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class CommandRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    granted_permissions: List[str] = Field(default_factory=list)
    confirmed_tool_ids: List[str] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


class CommandResponse(BaseModel):
    task_id: str
    intent: str
    status: str
    response: str
    steps: Optional[List[Dict[str, Any]]] = None
    confirmation_requests: Optional[List[Dict[str, Any]]] = None
    missing_permissions: Optional[List[str]] = None
    duration_ms: int


class ToolInfo(BaseModel):
    id: str
    name: str
    description: str
    risk_level: str
    confirmation_level: str
    required_permissions: List[str]
    tags: List[str]


class HistoryItem(BaseModel):
    task_id: str
    timestamp: str
    intent: str
    selected_tool: Optional[str]
    outcome: str
    response_preview: str
    duration_ms: Optional[int]


class MemoryEntryOut(BaseModel):
    id: str
    memory_type: str
    key: str
    value: Any
    created_at: str
    source: str


class RememberRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=10000)
    memory_type: str = "fact"


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "NIA Backend",
        "version": "0.1.0",
        "tools_registered": len(registry.list_tools()),
        "arc_available": arc_service.is_available(),
    }


# ---------------------------------------------------------------------------
# Main Command Endpoint
# ---------------------------------------------------------------------------

@router.post("/command", response_model=CommandResponse)
def process_command(
    req: CommandRequest,
    user_id: str = Depends(get_user_id),
) -> CommandResponse:
    task_id = new_task_id()
    t0 = time.monotonic()

    # Sanitize user input — raises 400 on suspected prompt injection
    try:
        safe_text = sanitize_user_input(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Run the orchestrator
    result = orchestrator.process(
        text=safe_text,
        granted_permissions=req.granted_permissions,
        confirmed_tool_ids=req.confirmed_tool_ids,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Determine outcome for history
    status_val = result.get("status", "completed")
    outcome_map = {
        "completed": TaskOutcome.SUCCESS,
        "failed": TaskOutcome.FAILED,
        "cancelled": TaskOutcome.CANCELLED,
        "permission_required": TaskOutcome.PERMISSION_DENIED,
        "awaiting_confirmation": TaskOutcome.AWAITING_CONFIRMATION,
    }
    outcome = outcome_map.get(status_val, TaskOutcome.SUCCESS)

    # Identify primary tool and parameters used
    steps = result.get("steps", [])
    selected_tool = steps[0]["tool_id"] if steps else None
    parameters = steps[0].get("result") or {} if steps else {}

    # Record to task history
    rec = build_record(
        task_id=task_id,
        user_id=user_id,
        raw_text=safe_text,
        intent=result.get("intent", "unknown"),
        selected_tool=selected_tool,
        parameters=parameters,
        permission_state="granted" if not result.get("missing_permissions") else "denied",
        confirmation_state=(
            "pending" if status_val == "awaiting_confirmation"
            else "not_required"
        ),
        outcome=outcome,
        execution_result={"steps": steps} if steps else None,
        verified=all(s.get("verified", False) for s in steps) if steps else False,
        failure_reason=result.get("response") if outcome == TaskOutcome.FAILED else None,
        duration_ms=duration_ms,
    )
    task_history.record(rec)

    return CommandResponse(
        task_id=task_id,
        intent=result.get("intent", "unknown"),
        status=status_val,
        response=result.get("response", ""),
        steps=steps or None,
        confirmation_requests=result.get("confirmation_requests"),
        missing_permissions=result.get("missing_permissions"),
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@router.get("/tools", response_model=List[ToolInfo])
def list_tools() -> List[ToolInfo]:
    return [
        ToolInfo(
            id=t.id,
            name=t.name,
            description=t.description,
            risk_level=t.risk_level.value,
            confirmation_level=t.confirmation_level.value,
            required_permissions=t.required_permissions,
            tags=t.tags,
        )
        for t in registry.list_tools()
    ]


# ---------------------------------------------------------------------------
# Task History
# ---------------------------------------------------------------------------

@router.get("/history", response_model=List[HistoryItem])
def get_history(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_user_id),
) -> List[HistoryItem]:
    records = task_history.get(user_id, limit=min(limit, 200), offset=offset)
    return [
        HistoryItem(
            task_id=r.task_id,
            timestamp=r.timestamp.isoformat(),
            intent=r.intent,
            selected_tool=r.selected_tool,
            outcome=r.outcome.value,
            response_preview=r.raw_text[:100],
            duration_ms=r.duration_ms,
        )
        for r in records
    ]


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@router.get("/memory", response_model=List[MemoryEntryOut])
def list_memory(
    memory_type: Optional[str] = None,
    user_id: str = Depends(get_user_id),
) -> List[MemoryEntryOut]:
    mt = MemoryType(memory_type) if memory_type else None
    entries = memory_service.list_memory(user_id, memory_type=mt)
    return [
        MemoryEntryOut(
            id=e.id,
            memory_type=e.memory_type.value,
            key=e.key,
            value=e.value,
            created_at=e.created_at.isoformat(),
            source=e.source,
        )
        for e in entries
    ]


@router.post("/memory", response_model=MemoryEntryOut, status_code=status.HTTP_201_CREATED)
def remember(
    req: RememberRequest,
    user_id: str = Depends(get_user_id),
) -> MemoryEntryOut:
    try:
        mt = MemoryType(req.memory_type)
        entry = memory_service.remember(user_id, req.key, req.value, memory_type=mt)
        return MemoryEntryOut(
            id=entry.id,
            memory_type=entry.memory_type.value,
            key=entry.key,
            value=entry.value,
            created_at=entry.created_at.isoformat(),
            source=entry.source,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/memory/{entry_id}")
def forget_one(
    entry_id: str,
    user_id: str = Depends(get_user_id),
) -> Dict[str, Any]:
    deleted = memory_service.forget(user_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found.")
    return {"deleted": True, "id": entry_id}


@router.delete("/memory")
def forget_all(user_id: str = Depends(get_user_id)) -> Dict[str, Any]:
    count = memory_service.forget_all(user_id)
    return {"deleted": count}


# ---------------------------------------------------------------------------
# Arc Status
# ---------------------------------------------------------------------------

@router.get("/arc/status")
def arc_status() -> Dict[str, Any]:
    return {
        "available": arc_service.is_available(),
        "features": {
            "agent_identity": False,
            "task_attestation": False,
            "usdc_payment": False,
            "agent_marketplace": False,
            "spending_policy": False,
        },
        "message": "Arc integration is planned for v0.2. All Arc features are disabled in v0.1.",
    }
