"""
NIA Backend — /api/v1/memory
Memory read/write/delete endpoints.
All writes go through MemoryPolicy before storage.
Users can always delete their entire memory.
"""
from __future__ import annotations

from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import get_current_user
from ...memory.memory_service import memory_service, MemoryType

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryWrite(BaseModel):
    key: str
    value: Any
    memory_type: MemoryType = MemoryType.FACT


class MemoryResponse(BaseModel):
    id: str
    key: str
    value: Any
    memory_type: str
    source: str
    created_at: str
    updated_at: str


class DeleteAllResponse(BaseModel):
    deleted_count: int
    message: str


@router.post("/", response_model=MemoryResponse, status_code=201)
async def remember(
    req: MemoryWrite,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    try:
        entry = memory_service.remember(
            user_id=current_user["id"],
            key=req.key,
            value=req.value,
            memory_type=req.memory_type,
            source="user_explicit",
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MemoryResponse(
        id=entry.id,
        key=entry.key,
        value=entry.value,
        memory_type=entry.memory_type.value,
        source=entry.source,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


@router.get("/", response_model=List[MemoryResponse])
async def list_memory(
    current_user: Annotated[dict, Depends(get_current_user)],
    memory_type: Optional[MemoryType] = None,
):
    entries = memory_service.list_memory(current_user["id"], memory_type=memory_type)
    return [
        MemoryResponse(
            id=e.id,
            key=e.key,
            value=e.value,
            memory_type=e.memory_type.value,
            source=e.source,
            created_at=e.created_at.isoformat(),
            updated_at=e.updated_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/{entry_id}", response_model=MemoryResponse)
async def get_memory(
    entry_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    entry = memory_service.repo.get(current_user["id"], entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Memory entry not found.")
    return MemoryResponse(
        id=entry.id,
        key=entry.key,
        value=entry.value,
        memory_type=entry.memory_type.value,
        source=entry.source,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


@router.delete("/{entry_id}", status_code=204)
async def forget(
    entry_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    deleted = memory_service.forget(current_user["id"], entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found.")


@router.delete("/", response_model=DeleteAllResponse)
async def forget_all(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    count = memory_service.forget_all(current_user["id"])
    return DeleteAllResponse(
        deleted_count=count,
        message=f"Deleted all {count} memory entries for your account.",
    )
