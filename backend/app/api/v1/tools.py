"""
NIA Backend — /api/v1/tools
Tool registry inspection and direct tool execution (with confirmation enforcement).
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import get_current_user
from ...tools.registry import registry, RiskLevel, ConfirmationLevel

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolInfo(BaseModel):
    id: str
    name: str
    description: str
    risk_level: str
    confirmation_level: str
    required_permissions: List[str]
    tags: List[str]


class ToolExecuteRequest(BaseModel):
    tool_id: str
    parameters: Dict[str, Any] = {}
    confirmed: bool = False   # Must be True for YELLOW/RED tools


class ToolExecuteResponse(BaseModel):
    tool_id: str
    result: Dict[str, Any]
    verified: bool


@router.get("/", response_model=List[ToolInfo])
async def list_tools(
    current_user: Annotated[dict, Depends(get_current_user)],
    risk_level: str = "",
):
    tools = registry.list_tools()
    if risk_level:
        try:
            rl = RiskLevel(risk_level.upper())
            tools = [t for t in tools if t.risk_level == rl]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown risk level: {risk_level!r}")
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
        for t in tools
    ]


@router.get("/{tool_id}", response_model=ToolInfo)
async def get_tool(
    tool_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    try:
        t = registry.get(tool_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found.")
    return ToolInfo(
        id=t.id,
        name=t.name,
        description=t.description,
        risk_level=t.risk_level.value,
        confirmation_level=t.confirmation_level.value,
        required_permissions=t.required_permissions,
        tags=t.tags,
    )


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    req: ToolExecuteRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Directly execute a tool. YELLOW/RED tools require confirmed=True.
    This endpoint enforces the confirmation check at the API layer.
    """
    try:
        tool = registry.get(req.tool_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_id}' not found.")

    if tool.confirmation_level in (ConfirmationLevel.YELLOW, ConfirmationLevel.RED) and not req.confirmed:
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool.id}' (risk={tool.risk_level.value}) requires explicit user confirmation. "
                   "Set confirmed=true after showing the user the confirmation dialog.",
        )

    # Execute
    if tool.execute_handler:
        try:
            result = tool.execute_handler(req.parameters)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Tool execution failed: {exc}") from exc
    else:
        result = {
            "status": "dispatched_to_client",
            "tool_id": tool.id,
            "parameters": req.parameters,
        }

    # Verify
    verified = False
    if tool.verify_handler:
        verified = tool.verify_handler(result)
    else:
        verified = bool(result) and "error" not in result

    return ToolExecuteResponse(tool_id=tool.id, result=result, verified=verified)
