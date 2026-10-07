"""
NIA — Shared Python Type Definitions (Pydantic)

This file is the canonical Python mirror of shared/types/nia.ts.
Import these in the backend instead of defining ad-hoc schemas.

Rule: keep in sync with nia.ts and the Kotlin data classes in android/.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ── Risk levels ──────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"


class ConfirmationLevel(str, Enum):
    AUTO    = "AUTO"    # GREEN  — execute immediately
    CONFIRM = "CONFIRM" # YELLOW — tap to confirm
    TYPED   = "TYPED"   # RED    — type "confirm"


# ── Agent states ─────────────────────────────────────────────────────────────

class AgentState(str, Enum):
    IDLE        = "idle"
    LISTENING   = "listening"
    PROCESSING  = "processing"
    CONFIRMING  = "confirming"
    EXECUTING   = "executing"
    SPEAKING    = "speaking"
    ERROR       = "error"


# ── Tools ─────────────────────────────────────────────────────────────────────

class ToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    risk: RiskLevel
    confirmation_level: ConfirmationLevel
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    required_permissions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


# ── Confirmation ──────────────────────────────────────────────────────────────

class ConfirmationRequest(BaseModel):
    tool_id: str
    tool_name: str
    description: str
    risk_level: RiskLevel
    confirmation_level: ConfirmationLevel
    prompt: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


# ── Orchestrator pipeline ─────────────────────────────────────────────────────

class PipelineStep(BaseModel):
    step: str
    input: Optional[Any] = None
    output: Optional[Any] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


# ── API request / response ────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class AssistantRequest(BaseModel):
    text: str
    granted_permissions: List[str] = Field(default_factory=list)
    confirmed_tool_ids: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


class AssistantResponse(BaseModel):
    intent: str
    status: str
    response: str
    steps: List[PipelineStep] = Field(default_factory=list)
    confirmation_requests: List[ConfirmationRequest] = Field(default_factory=list)
    missing_permissions: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


# ── Memory ────────────────────────────────────────────────────────────────────

class MemoryCategory(str, Enum):
    PREFERENCE           = "preference"
    FACT                 = "fact"
    TASK_HISTORY         = "task_history"
    CONVERSATION_SUMMARY = "conversation_summary"
    RECURRING_TASK       = "recurring_task"


class MemorySource(str, Enum):
    USER_EXPLICIT = "user_explicit"
    INFERRED      = "inferred"


class MemoryEntry(BaseModel):
    id: str
    category: MemoryCategory
    key: str
    value: str
    source: MemorySource
    created_at: datetime
    updated_at: datetime


# ── Task record ───────────────────────────────────────────────────────────────

class TaskRecord(BaseModel):
    id: str
    user_id: str
    command: str
    intent: str
    tool_id: Optional[str] = None
    status: TaskStatus
    response: Optional[str] = None
    steps: List[PipelineStep] = Field(default_factory=list)
    duration_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ── Arc (prepared, not active in v0.1) ────────────────────────────────────────

class ArcAgentIdentity(BaseModel):
    agent_id: str           # ERC-8004 token ID
    wallet_address: str
    chain_id: int
    name: str
    description: str


class ArcSpendingPolicy(BaseModel):
    max_per_transaction: int = 0   # USDC cents
    max_per_day: int = 0           # USDC cents
    require_confirmation_above: int = 0
    allowed_service_ids: List[str] = Field(default_factory=list)


class ArcPaymentIntent(BaseModel):
    service_id: str
    amount: int             # USDC cents
    description: str
    task_id: str
