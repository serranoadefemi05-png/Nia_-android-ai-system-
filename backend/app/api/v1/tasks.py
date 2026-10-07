"""
NIA Backend — /api/v1/tasks
Task history: list, get, update status, delete.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

# In-memory store (replace with DB in production)
_tasks: dict[str, dict] = {}  # { task_id: task }


class TaskCreate(BaseModel):
    title: str
    intent: str
    tool_ids: List[str] = []
    raw_command: str = ""


class TaskResponse(BaseModel):
    id: str
    user_id: str
    title: str
    intent: str
    tool_ids: List[str]
    raw_command: str
    status: str
    created_at: str
    updated_at: str


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    req: TaskCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    now = datetime.now(timezone.utc).isoformat()
    task = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "title": req.title,
        "intent": req.intent,
        "tool_ids": req.tool_ids,
        "raw_command": req.raw_command,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    _tasks[task["id"]] = task
    return TaskResponse(**task)


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    current_user: Annotated[dict, Depends(get_current_user)],
    status: Optional[str] = None,
    limit: int = 50,
):
    tasks = [t for t in _tasks.values() if t["user_id"] == current_user["id"]]
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    tasks.sort(key=lambda t: t["created_at"], reverse=True)
    return [TaskResponse(**t) for t in tasks[:limit]]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    task = _tasks.get(task_id)
    if task is None or task["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse(**task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    req: TaskUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    task = _tasks.get(task_id)
    if task is None or task["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Task not found.")
    if req.status:
        task["status"] = req.status
    if req.title:
        task["title"] = req.title
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    return TaskResponse(**task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    task = _tasks.get(task_id)
    if task is None or task["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Task not found.")
    del _tasks[task_id]
