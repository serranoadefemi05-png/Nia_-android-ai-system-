"""
NIA Browser Agent — Basic Provider

A minimal, safe web content fetcher using httpx. No headless browser required.

This is NOT a full browser agent. It:
  - Fetches the text content of a URL
  - Strips HTML tags
  - Truncates to a safe size
  - Wraps the result as EXTERNAL CONTENT (security.py)

It is the safe default for web_search tool results that need a full-page read.
The DejevuProvider (dejevu_stub.py) is the future path for multi-step web tasks.
"""
from __future__ import annotations

import html
import logging
import re
from typing import Optional

import httpx

from ..core.security import wrap_external_content, check_ssrf
from .provider import BrowserAgentProvider, BrowserResult, BrowserProviderError

logger = logging.getLogger("nia.browser_agent.basic")

_MAX_CONTENT_CHARS = 8192
_FETCH_TIMEOUT = 15.0

# Minimal set of HTML tags to strip
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s{3,}")


def _strip_html(raw: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub("\n\n", text)
    return text.strip()


class BasicProvider(BrowserAgentProvider):
    """
    httpx-based text fetcher.  Returns page text; no JavaScript execution.
    """

    def is_available(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "basic"

    async def run(
        self,
        goal: str,
        start_url: Optional[str] = None,
    ) -> BrowserResult:
        """
        Fetch `start_url` and return its text content, wrapped as external data.

        The goal is NOT used to drive multi-step navigation — that would require
        a real browser. It is recorded in the result for logging.
        """
        if not start_url:
            return BrowserResult(
                goal=goal,
                status="blocked",
                error="BasicProvider requires a start_url. No URL was provided.",
            )

        # SSRF check
        try:
            check_ssrf(start_url)
        except ValueError as exc:
            raise BrowserProviderError(f"SSRF check failed: {exc}") from exc

        try:
            async with httpx.AsyncClient(
                timeout=_FETCH_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "NIA-Agent/0.3 (+https://nia.ai)"},
            ) as client:
                resp = await client.get(start_url)
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            return BrowserResult(
                goal=goal,
                status="error",
                url=start_url,
                error=f"Request timed out after {_FETCH_TIMEOUT}s.",
            )
        except httpx.HTTPStatusError as exc:
            return BrowserResult(
                goal=goal,
                status="error",
                url=str(exc.request.url),
                error=f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}",
            )
        except Exception as exc:
            return BrowserResult(
                goal=goal,
                status="error",
                url=start_url,
                error=str(exc),
            )

        raw = resp.text
        text = _strip_html(raw)[:_MAX_CONTENT_CHARS]

        # Wrap as external content so the LLM treats it as data, not instructions
        wrapped = wrap_external_content(text, source=start_url)

        logger.info(
            "BASIC_FETCH url=%s status=%d text_len=%d",
            resp.url, resp.status_code, len(text),
        )

        return BrowserResult(
            goal=goal,
            status="done",
            url=str(resp.url),
            extracted_text=wrapped,
            actions_taken=1,
            requests_made=1,
        )
