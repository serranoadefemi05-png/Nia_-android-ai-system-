"""
NIA Backend — /api/v1/web
Web search and retrieval via WebAgentProvider.
All URLs are SSRF-validated. All fetched content is wrapped before LLM use.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from .auth import get_current_user
from ...web.web_agent import get_web_agent, SearchResult
from ...core.config import settings
from ...core.security import validate_web_url

router = APIRouter(prefix="/web", tags=["web"])

_agent = get_web_agent(settings.WEB_AGENT_PROVIDER)


class SearchRequest(BaseModel):
    query: str
    num_results: int = 5


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, str]]
    summary: str


class BrowseRequest(BaseModel):
    url: str


class BrowseResponse(BaseModel):
    url: str
    title: str
    content: str


@router.post("/search", response_model=SearchResponse)
async def web_search(
    req: SearchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    results = _agent.search(req.query.strip(), num_results=min(req.num_results, 10))
    summary = results[0].snippet if results else "No results found."
    return SearchResponse(
        query=req.query,
        results=[{"title": r.title, "url": r.url, "snippet": r.snippet, "source": r.source} for r in results],
        summary=summary,
    )


@router.post("/browse", response_model=BrowseResponse)
async def browse_url(
    req: BrowseRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    try:
        validate_web_url(req.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    page = _agent.browse(req.url)
    return BrowseResponse(url=page.url, title=page.title, content=page.text)
