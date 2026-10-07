"""
NIA Backend — Tool Registry
Central registry of every tool the AI orchestrator can request.
Every tool has: id, description, schemas, risk level, confirmation level,
required permissions, optional execution handler, optional verification handler.

HIGH/CRITICAL tools are never executed without confirmed=True.
Tool execution enforced at both the orchestrator AND the API layer.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfirmationLevel(str, enum.Enum):
    GREEN = "GREEN"      # Auto-execute — safe
    YELLOW = "YELLOW"    # Confirm before execute
    RED = "RED"          # Explicit typed confirmation required


@dataclass
class ToolParam:
    name: str
    type: str                   # "string" | "integer" | "boolean" | "object" | "array"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    id: str
    name: str
    description: str
    risk_level: RiskLevel
    confirmation_level: ConfirmationLevel
    required_permissions: List[str] = field(default_factory=list)
    input_params: List[ToolParam] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    execute_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    verify_handler: Optional[Callable[[Dict[str, Any]], bool]] = None

    def to_llm_description(self) -> Dict[str, Any]:
        """Returns a safe, schema-level view for LLM prompting."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "confirmation_level": self.confirmation_level.value,
            "required_permissions": self.required_permissions,
            "input_params": [
                {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                for p in self.input_params
            ],
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        assert tool.id not in self._tools, f"Tool already registered: {tool.id!r}"
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> Tool:
        if tool_id not in self._tools:
            raise KeyError(f"Tool not found: {tool_id!r}")
        return self._tools[tool_id]

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def requires_confirmation(self, tool_id: str) -> bool:
        return self.get(tool_id).confirmation_level != ConfirmationLevel.GREEN

    def to_llm_descriptions(self) -> List[Dict[str, Any]]:
        return [t.to_llm_description() for t in self._tools.values()]


# ── Global registry + built-in tools ──────────────────────────────────────

registry = ToolRegistry()

_TOOLS = [
    Tool(id="take_screenshot", name="Take Screenshot", description="Capture the current screen and save to gallery.",
         risk_level=RiskLevel.LOW, confirmation_level=ConfirmationLevel.GREEN,
         required_permissions=["MEDIA_PROJECTION"], tags=["screenshot", "screen"]),

    Tool(id="search_local_files", name="Search Local Files", description="Search user-authorized local storage by file type and date.",
         risk_level=RiskLevel.LOW, confirmation_level=ConfirmationLevel.GREEN,
         required_permissions=["READ_EXTERNAL_STORAGE"], tags=["files", "pdf", "documents"],
         input_params=[ToolParam("query", "string", "Search terms"), ToolParam("file_type", "string", "Extension e.g. pdf", required=False), ToolParam("date_hint", "string", "yesterday|today|last_week", required=False)]),

    Tool(id="create_reminder", name="Create Reminder", description="Create a reminder or alarm at a specified time.",
         risk_level=RiskLevel.LOW, confirmation_level=ConfirmationLevel.GREEN,
         required_permissions=["SET_ALARM"], tags=["reminder", "alarm"],
         input_params=[ToolParam("title", "string", "Reminder title"), ToolParam("hour", "integer", "Hour 0-23"), ToolParam("minute", "integer", "Minute 0-59"), ToolParam("message", "string", "Optional message", required=False)]),

    Tool(id="web_search", name="Web Search", description="Search the web and return summarized results.",
         risk_level=RiskLevel.LOW, confirmation_level=ConfirmationLevel.GREEN, tags=["web", "search"],
         input_params=[ToolParam("query", "string", "Search query"), ToolParam("num_results", "integer", "Result count", required=False, default=5)]),

    Tool(id="open_app", name="Open App", description="Launch a named Android application.",
         risk_level=RiskLevel.LOW, confirmation_level=ConfirmationLevel.GREEN, tags=["app", "launch"],
         input_params=[ToolParam("app_name", "string", "Common name e.g. WhatsApp")]),

    Tool(id="read_notification", name="Read Notification", description="Read a specific notification the user grants access to.",
         risk_level=RiskLevel.LOW, confirmation_level=ConfirmationLevel.GREEN,
         required_permissions=["BIND_NOTIFICATION_LISTENER_SERVICE"], tags=["notification"]),

    Tool(id="send_message", name="Send Message", description="Send a message via WhatsApp, SMS, or another app.",
         risk_level=RiskLevel.HIGH, confirmation_level=ConfirmationLevel.YELLOW,
         required_permissions=["SEND_SMS"], tags=["message", "sms"],
         input_params=[ToolParam("recipient", "string", "Phone number or contact name"), ToolParam("body", "string", "Message text"), ToolParam("channel", "string", "whatsapp|sms|telegram", required=False)]),

    Tool(id="delete_file", name="Delete File", description="Permanently delete a file from local storage.",
         risk_level=RiskLevel.HIGH, confirmation_level=ConfirmationLevel.YELLOW,
         required_permissions=["MANAGE_EXTERNAL_STORAGE"], tags=["delete", "file"],
         input_params=[ToolParam("path", "string", "File path to delete")]),

    Tool(id="make_payment", name="Make Payment", description="Initiate a USDC or local currency payment.",
         risk_level=RiskLevel.CRITICAL, confirmation_level=ConfirmationLevel.RED,
         required_permissions=["INTERNET"], tags=["payment", "usdc", "arc"],
         input_params=[ToolParam("to_address", "string", "Recipient address or identifier"), ToolParam("amount_usdc", "string", "Amount in USDC"), ToolParam("description", "string", "Payment description")]),
]

for _tool in _TOOLS:
    registry.register(_tool)
