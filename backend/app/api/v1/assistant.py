"""
NIA Backend — /api/v1/assistant
Main AI orchestration endpoint.
Handles text commands + WebSocket streaming for real-time voice interaction.
"""
from __future__ import annotations

import json
import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .auth import get_current_user
from ...core.security import sanitize_user_input
from ...orchestrator.orchestrator import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


# ── Schemas ────────────────────────────────────────────────────────────────

class AssistantRequest(BaseModel):
    text: str
    granted_permissions: List[str] = []
    confirmed_tool_ids: List[str] = []
    session_id: Optional[str] = None
    # Tool result callback — set when Android is reporting back after executing a tool.
    # The Android app calls this endpoint TWICE for tool-using interactions:
    #   1. text command → backend dispatches tool (status="dispatched")
    #   2. tool_result callback → backend observes + responds (status="completed")
    tool_result: Optional[Dict[str, Any]] = None


class AssistantResponse(BaseModel):
    intent: str
    status: str
    response: str
    steps: List[Dict[str, Any]] = []
    confirmation_requests: List[Dict[str, Any]] = []
    missing_permissions: List[str] = []
    session_id: Optional[str] = None
    tool_id: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    awaiting_tool_result: bool = False


# ── REST endpoint ──────────────────────────────────────────────────────────

@router.post("/command", response_model=AssistantResponse)
@router.post("/", response_model=AssistantResponse)
async def process_command(
    req: AssistantRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Process a single text command through the full NIA orchestration pipeline.

    Two-phase flow for tool-using commands:
      Phase 1: Android sends { text: "take a screenshot" }
               Backend returns { status: "dispatched", tool_id: "take_screenshot", awaiting_tool_result: true }
               Android executes the tool.

      Phase 2: Android sends { text: "take a screenshot", tool_result: { tool_id: "take_screenshot", success: true, data: {...} } }
               Backend validates result, generates TTS response, returns { status: "completed", response: "..." }

    For conversational commands: single round-trip, no tool_result needed.
    """
    user_id = current_user.get("sub", "anonymous")

    try:
        text = sanitize_user_input(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await orchestrator.process_async(
        text=text,
        granted_permissions=req.granted_permissions,
        confirmed_tool_ids=req.confirmed_tool_ids,
        user_id=user_id,
        tool_result=req.tool_result,
    )

    return AssistantResponse(
        intent=result.get("intent", "unknown"),
        status=result.get("status", "unknown"),
        response=result.get("response", ""),
        steps=result.get("steps", []),
        confirmation_requests=result.get("confirmation_requests", []),
        missing_permissions=result.get("missing_permissions", []),
        session_id=req.session_id,
        tool_id=result.get("tool_id"),
        tool_params=result.get("tool_params"),
        awaiting_tool_result=result.get("awaiting_tool_result", False),
    )


# ── WebSocket endpoint (streaming / voice) ─────────────────────────────────

@router.websocket("/ws/{user_id}")
async def assistant_websocket(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time voice interaction.
    Protocol:
      Client → { "type": "command", "text": "...", "permissions": [...], "confirmed": [...] }
      Server → { "type": "partial", "text": "..." }         (streaming partial response)
      Server → { "type": "result", ...AssistantResponse }   (final result)
      Server → { "type": "confirmation", ...request }       (confirmation needed)
      Server → { "type": "error", "message": "..." }
    """
    await websocket.accept()
    logger.info("WS connected: user_id=%s", user_id)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON."})
                continue

            if msg.get("type") != "command":
                await websocket.send_json({"type": "error", "message": "Unknown message type."})
                continue

            text = msg.get("text", "")
            try:
                text = sanitize_user_input(text)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            # Stream a "thinking" partial immediately
            await websocket.send_json({"type": "partial", "text": "Processing..."})

            result = await orchestrator.process_async(
                text=text,
                granted_permissions=msg.get("permissions", []),
                confirmed_tool_ids=msg.get("confirmed", []),
            )

            if result.get("status") == "awaiting_confirmation":
                await websocket.send_json({
                    "type": "confirmation",
                    "confirmation_requests": result.get("confirmation_requests", []),
                    "response": result.get("response", ""),
                })
            else:
                await websocket.send_json({
                    "type": "result",
                    "intent": result.get("intent", "unknown"),
                    "status": result.get("status", "unknown"),
                    "response": result.get("response", ""),
                    "steps": result.get("steps", []),
                    "missing_permissions": result.get("missing_permissions", []),
                })
    except WebSocketDisconnect:
        logger.info("WS disconnected: user_id=%s", user_id)
    except Exception as exc:
        logger.error("WS error for user %s: %s", user_id, exc)
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error."})
        except Exception:
            pass
