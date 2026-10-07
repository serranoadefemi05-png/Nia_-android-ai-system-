"""
NIA Backend — Health endpoints

GET  /api/v1/health   — Liveness: process is alive
GET  /api/v1/ready    — Readiness: all subsystems operational
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ...tools.registry import registry

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Liveness probe — returns 200 as long as the process is alive."""
    from ...llm.provider import get_llm_provider
    from ...arc.arc_service import arc_service
    from ...browser_agent.provider import get_browser_agent_provider
    provider = get_llm_provider()
    browser_provider = get_browser_agent_provider()
    return {
        "status": "ok",
        "service": "NIA Backend",
        "version": "0.3.0",
        "architecture": "openyabby-inspired",
        "tools_registered": len(registry.list_tools()),
        "ai": {
            "provider": provider.provider_name(),
            "model": provider.model_name(),
            "configured": provider.is_configured(),
            # NOTE: never expose the actual key value — only a boolean
        },
        "browser_agent": {
            "provider": browser_provider.provider_name(),
            "available": browser_provider.is_available(),
        },
        "arc": arc_service.status(),
    }


@router.get("/ready")
def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe — returns 503 if the AI provider is not configured.
    Suitable for Kubernetes readinessProbe and Android health preflight checks.
    """
    from fastapi import HTTPException
    from ...llm.provider import get_llm_provider

    provider = get_llm_provider()
    issues = []

    if not provider.is_configured():
        issues.append(
            f"AI provider '{provider.provider_name()}' is not configured "
            f"(missing API key or credentials)."
        )

    if issues:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "issues": issues},
        )

    return {
        "status": "ready",
        "ai_provider": provider.provider_name(),
        "ai_model": provider.model_name(),
        "tools_registered": len(registry.list_tools()),
    }
