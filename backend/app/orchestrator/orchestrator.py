"""
NIA Backend — Agent Orchestrator  (v0.3 — OpenYabby-inspired architecture)

Pipeline (observe → plan → confirm → dispatch → observe result → respond):

  sanitized user text
  → Planner.plan()           ← LLM call → intent + optional tool request
  → permission check
  → confirmation check
  → tool dispatch to Android (or direct conversational reply)
  → [Android executes tool and returns result]
  → Observer.observe()       ← validate result, detect injection, size-bound
  → Responder.respond_after_tool()  ← second LLM call: TTS-ready summary
  → conversation_memory.add_turn()  ← persist for future context
  → return structured result

Architecture changes from v0.2:
  - Planner, Observer, Responder are now separate modules (agent package)
  - ConversationMemory tracks turn history server-side (memory.conversation)
  - OpenRouterProvider added to llm/provider.py (free OSS models)
  - Loop detection in Planner (same tool called >3 times = PlannerLoopError)
  - Hallucination guard: backend NEVER claims tool succeeded; Android reports result
  - BrowserAgentProvider for web_search tool (browser_agent package)

Inspired by (NOT copied from):
  - OpenYabby observe→plan→act loop (lib/agent-task-processor.js)
  - dejevu observe→decide→guard→act→settle loop (dejevu/agent.py)
  - OpenYabby hallucination-detector.js
  - OpenYabby retry-detector.js
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..agent.planner import Planner, PlannerLoopError, PlannerResult
from ..agent.observer import Observer
from ..agent.responder import Responder
from ..llm.provider import LLMNotConfiguredError, LLMResponseError, LLMTimeoutError, get_llm_provider
from ..tools.registry import ConfirmationLevel, registry
from ..memory.memory_service import MemoryType, memory_service
from ..memory.conversation import conversation_memory

logger = logging.getLogger("nia.orchestrator")


class Orchestrator:
    """
    NIA's agent orchestration pipeline.

    One Orchestrator instance is shared across all requests (singleton pattern).
    Each request gets a fresh Planner instance (for loop detection per session).
    Observer and Responder are stateless and shared.
    """

    def __init__(self) -> None:
        self._observer = Observer()
        self._responder = Responder()

    # ── Public async entry point ───────────────────────────────────────────

    async def process_async(
        self,
        text: str,
        granted_permissions: Optional[List[str]] = None,
        confirmed_tool_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Full NIA agent pipeline. Returns a structured dict.

        Args:
          text:                 sanitized user utterance
          granted_permissions:  list of Android permission names already granted
          confirmed_tool_ids:   list of tool_ids the user explicitly confirmed
          user_id:              device-id or session token (from X-Device-Id header)
          conversation_history: recent turns if passed by Android client
                                (superseded by server-side ConversationMemory when available)
          tool_result:          if present, this is a tool-result callback from Android;
                                skip planning and go straight to observe+respond

        The 'tool_result' path implements the second half of the pipeline:
          Android executes tool → sends result back → Observer validates → Responder speaks
        """
        granted = set(granted_permissions or [])
        confirmed = set(confirmed_tool_ids or [])
        steps: List[Dict[str, Any]] = []

        # ── Use server-side conversation history if available ──────────────
        if user_id:
            server_history = conversation_memory.get_history(user_id, last_n=6)
            if server_history:
                # Server history takes precedence over client-supplied history
                conversation_history = server_history

        # ── Tool result callback path ──────────────────────────────────────
        # Android executed a tool and is reporting back. Skip planning.
        if tool_result is not None:
            return await self._handle_tool_result(
                text=text,
                tool_result=tool_result,
                conversation_history=conversation_history,
                user_id=user_id,
                steps=steps,
            )

        # ── Check provider is configured ───────────────────────────────────
        provider = get_llm_provider()
        if not provider.is_configured():
            return {
                "intent": "error",
                "status": "error",
                "steps": [{"step": "provider_check", "result": "not_configured"}],
                "response": (
                    "NIA's AI provider is not configured yet. "
                    "Please ask your administrator to set the API credentials."
                ),
            }

        # ── Step 1: Planner — intent + tool selection ──────────────────────
        planner = Planner()
        try:
            plan: PlannerResult = await planner.plan(
                user_message=text,
                conversation_history=conversation_history,
            )
        except LLMNotConfiguredError as exc:
            logger.warning("LLM not configured: %s", exc)
            return _error_result("not_configured", str(exc), steps)
        except LLMTimeoutError as exc:
            logger.warning("LLM timeout: %s", exc)
            return _error_result(
                "timeout",
                "I'm sorry, the AI took too long to respond. Please try again in a moment.",
                steps,
            )
        except LLMResponseError as exc:
            logger.error("LLM response error: %s", exc)
            return _error_result(
                "parse_error",
                "I received an unexpected response from my AI provider. Please try again.",
                steps,
            )
        except PlannerLoopError as exc:
            logger.warning("Planner loop detected: %s", exc)
            return _error_result(
                "loop_detected",
                "I seem to be going in circles. Let me stop and ask: could you rephrase what you'd like me to do?",
                steps,
            )
        except Exception as exc:
            logger.exception("Unexpected planner error: %s", exc)
            return _error_result("unexpected_error", "An unexpected error occurred. Please try again.", steps)

        steps.append({
            "step": "plan",
            "result": "ok",
            "provider": plan.provider,
            "model": plan.model,
            "intent": plan.intent,
            "tool": plan.tool_call.tool_id if plan.tool_call else None,
        })

        # ── Step 2: Conversational reply (no tool) ─────────────────────────
        if plan.is_conversational:
            response_text = await self._responder.respond_conversational(plan.response)
            steps.append({"step": "dispatch", "result": "conversational"})
            self._save_turns(user_id, text, response_text)
            self._save_memory(user_id, text, plan.intent, {})
            return {
                "intent": plan.intent,
                "status": "completed",
                "steps": steps,
                "response": response_text,
            }

        tool_id = plan.tool_call.tool_id

        # ── Step 3: Tool registry lookup ───────────────────────────────────
        try:
            tool = registry.get(tool_id)
        except KeyError:
            logger.error("Planner requested unregistered tool: %s", tool_id)
            steps.append({"step": "tool_lookup", "result": "not_found"})
            return {
                "intent": plan.intent,
                "status": "error",
                "steps": steps,
                "response": f"I tried to use a tool called '{tool_id}' but it isn't available right now.",
            }
        steps.append({"step": "tool_lookup", "result": "found", "tool_id": tool_id})

        # ── Step 4: Permission check ───────────────────────────────────────
        missing_perms = [p for p in tool.required_permissions if p not in granted]
        if missing_perms:
            steps.append({"step": "permission_check", "result": "missing", "missing": missing_perms})
            perm_names = ", ".join(missing_perms)
            s = "s" if len(missing_perms) > 1 else ""
            return {
                "intent": plan.intent,
                "status": "permission_required",
                "missing_permissions": missing_perms,
                "steps": steps,
                "response": (
                    f"To do that, I need the following Android permission{s}: {perm_names}. "
                    "Please grant them in your device settings."
                ),
            }
        steps.append({"step": "permission_check", "result": "ok"})

        # ── Step 5: Confirmation check (enforced at execution layer) ───────
        needs_confirmation = (
            tool.confirmation_level != ConfirmationLevel.GREEN
            or plan.tool_call.requires_confirmation
        )
        if needs_confirmation and tool_id not in confirmed:
            steps.append({
                "step": "confirmation_check",
                "result": "required",
                "level": tool.confirmation_level.value,
            })
            risk_msg = {
                ConfirmationLevel.YELLOW: "This action requires your confirmation before I proceed.",
                ConfirmationLevel.RED: (
                    "This is a high-risk action with potentially serious consequences. "
                    "Explicit confirmation is required."
                ),
            }.get(tool.confirmation_level, "Confirmation required.")
            return {
                "intent": plan.intent,
                "status": "awaiting_confirmation",
                "confirmation_requests": [{
                    "tool_id": tool_id,
                    "description": tool.description,
                    "confirmation_level": tool.confirmation_level.value,
                    "risk_level": tool.risk_level.value,
                    "prompt": risk_msg,
                }],
                "steps": steps,
                "response": risk_msg,
            }
        steps.append({"step": "confirmation_check", "result": "passed"})

        # ── Step 6: Validate tool arguments ───────────────────────────────
        params = plan.tool_call.arguments
        validation_error = _validate_tool_params(tool_id, params)
        if validation_error:
            steps.append({"step": "param_validation", "result": "error", "detail": validation_error})
            return {
                "intent": plan.intent,
                "status": "error",
                "steps": steps,
                "response": f"I couldn't complete that action: {validation_error}",
            }
        steps.append({"step": "param_validation", "result": "ok"})

        # ── Step 7: Dispatch to Android (or run server-side for web tools) ─
        # The Android client is the execution authority for all device tools.
        # The backend handles web_search server-side via BrowserAgentProvider.
        if tool_id == "web_search" and tool.execute_handler is None:
            # Run web search server-side
            server_result = await self._run_web_search(params)
            steps.append({"step": "execution", "result": "server_side", "data": server_result})

            # Observe the server-side result
            obs = self._observer.observe(
                expected_tool_id=tool_id,
                raw_result={"tool_id": tool_id, "success": server_result.get("success", True), "data": server_result},
            )

            # Generate TTS response
            response_text = await self._responder.respond_after_tool(
                original_message=text,
                tool_id=tool_id,
                tool_arguments=params,
                observation_data=obs.data_for_llm,
                observation_success=obs.success,
                conversation_history=conversation_history,
            )
            self._save_turns(user_id, text, response_text)
            self._save_memory(user_id, text, plan.intent, params)
            return {
                "intent": plan.intent,
                "status": "completed",
                "steps": steps,
                "response": response_text,
                "tool_id": tool_id,
                "tool_params": params,
                "confirmation_level": tool.confirmation_level.value,
            }

        # All other tools: dispatch to Android client
        # The client will execute the tool and call back with the result.
        steps.append({"step": "execution", "result": "dispatched_to_client"})

        # Provisional spoken response (TTS while Android executes)
        provisional_response = plan.response

        self._save_memory(user_id, text, plan.intent, params)

        return {
            "intent": plan.intent,
            "status": "dispatched",
            "steps": steps,
            "response": provisional_response,
            "tool_id": tool_id,
            "tool_params": params,
            "confirmation_level": tool.confirmation_level.value,
            # Android must call back with tool_result to complete the pipeline
            "awaiting_tool_result": True,
        }

    # ── Tool result callback ───────────────────────────────────────────────

    async def _handle_tool_result(
        self,
        text: str,
        tool_result: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]],
        user_id: Optional[str],
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Handle a tool result sent back from the Android client.
        Observer validates, Responder generates final TTS response.
        """
        expected_tool_id = tool_result.get("tool_id", "unknown")
        steps.append({"step": "tool_result_received", "tool_id": expected_tool_id})

        obs = self._observer.observe(
            expected_tool_id=expected_tool_id,
            raw_result=tool_result,
        )
        steps.append({
            "step": "observation",
            "result": "ok" if obs.success else "failed",
            "warning": obs.warning,
        })

        response_text = await self._responder.respond_after_tool(
            original_message=text,
            tool_id=expected_tool_id,
            tool_arguments=tool_result.get("arguments", {}),
            observation_data=obs.data_for_llm,
            observation_success=obs.success,
            conversation_history=conversation_history,
        )
        steps.append({"step": "respond", "result": "ok"})
        self._save_turns(user_id, text, response_text)

        return {
            "intent": tool_result.get("intent", expected_tool_id),
            "status": "completed" if obs.success else "completed_with_errors",
            "steps": steps,
            "response": response_text,
            "tool_id": expected_tool_id,
            "observation_warning": obs.warning,
        }

    # ── Web search (server-side) ────────────────────────────────────────────

    async def _run_web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a web search using the configured BrowserAgentProvider."""
        from ..browser_agent.provider import get_browser_agent_provider, BrowserProviderError
        query = params.get("query", "")
        try:
            provider = get_browser_agent_provider()
            if not provider.is_available():
                return {"success": False, "error": "Web search provider is not available.", "query": query}
            # Build a search URL (DuckDuckGo — no API key required)
            import urllib.parse
            search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            result = await provider.run(goal=f"Find information about: {query}", start_url=search_url)
            return {
                "success": result.status == "done",
                "query": query,
                "url": result.url,
                "content": result.extracted_text or "",
                "error": result.error,
            }
        except BrowserProviderError as exc:
            return {"success": False, "error": str(exc), "query": query}
        except Exception as exc:
            logger.exception("Web search error: %s", exc)
            return {"success": False, "error": str(exc), "query": query}

    # ── Synchronous wrapper (for test compatibility) ───────────────────────

    def process(
        self,
        text: str,
        granted_permissions: Optional[List[str]] = None,
        confirmed_tool_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper. FastAPI async routes should use process_async() directly."""
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.process_async(
                            text=text,
                            granted_permissions=granted_permissions,
                            confirmed_tool_ids=confirmed_tool_ids,
                            user_id=user_id,
                            conversation_history=conversation_history,
                            tool_result=tool_result,
                        ),
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(
                    self.process_async(
                        text=text,
                        granted_permissions=granted_permissions,
                        confirmed_tool_ids=confirmed_tool_ids,
                        user_id=user_id,
                        conversation_history=conversation_history,
                        tool_result=tool_result,
                    )
                )
        except Exception as exc:
            logger.exception("Orchestrator.process() error: %s", exc)
            return {
                "intent": "error",
                "status": "error",
                "steps": [],
                "response": "An unexpected error occurred.",
            }

    # ── Private helpers ────────────────────────────────────────────────────

    def _save_turns(
        self,
        user_id: Optional[str],
        user_text: str,
        assistant_text: str,
    ) -> None:
        if not user_id:
            return
        try:
            conversation_memory.add_turn(user_id, "user", user_text)
            conversation_memory.add_turn(user_id, "assistant", assistant_text)
        except Exception:
            pass  # Conversation memory failure never blocks the main result

    @staticmethod
    def _save_memory(
        user_id: Optional[str],
        text: str,
        intent: str,
        params: Dict[str, Any],
    ) -> None:
        if not user_id:
            return
        try:
            memory_service.remember(
                user_id=user_id,
                key=f"last_task_{intent}",
                value={"text": text, "intent": intent, "params": params},
                memory_type=MemoryType.TASK_HISTORY,
                source="orchestrator_summary",
            )
        except Exception:
            pass


# ── Private helpers ────────────────────────────────────────────────────────────

def _error_result(
    step_result: str,
    message: str,
    steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    steps.append({"step": "plan", "result": step_result})
    return {
        "intent": "error",
        "status": "error",
        "steps": steps,
        "response": message,
    }


def _validate_tool_params(tool_id: str, params: Dict[str, Any]) -> Optional[str]:
    """Lightweight parameter validation. Returns error string or None."""
    try:
        tool = registry.get(tool_id)
    except KeyError:
        return f"Unknown tool: {tool_id}"

    for param in tool.input_params:
        if param.required and param.name not in params:
            return f"Missing required parameter '{param.name}' for tool '{tool_id}'."
        if param.name in params:
            val = params[param.name]
            if param.type == "integer" and not isinstance(val, int):
                try:
                    params[param.name] = int(val)
                except (TypeError, ValueError):
                    return f"Parameter '{param.name}' must be an integer, got {type(val).__name__!r}."
            elif param.type == "string" and not isinstance(val, str):
                params[param.name] = str(val)
            elif param.type == "boolean" and not isinstance(val, bool):
                params[param.name] = bool(val)

    return None


# Module-level singleton
orchestrator = Orchestrator()
