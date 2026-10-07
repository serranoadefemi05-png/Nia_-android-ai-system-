"""
NIA Backend — Web Agent Provider
Abstraction layer: WebAgentProvider interface + basic HTTP implementation.
Future: plug in Playwright, Dejevu, or another browser-agent behind this interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import httpx


# ── Data models ────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


@dataclass
class BrowsedPage:
    url: str
    title: str
    text: str
    status_code: int


# ── Interface ──────────────────────────────────────────────────────────────

class WebAgentProvider:
    """
    Base interface. All web agent implementations must extend this.
    Designed so Dejevu, Playwright, or any other browser-agent system
    can be plugged in without restructuring NIA.
    """

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        raise NotImplementedError

    def browse(self, url: str) -> BrowsedPage:
        raise NotImplementedError

    def extract(self, url: str, selector: str) -> List[str]:
        raise NotImplementedError

    def interact(self, url: str, actions: list) -> dict:
        """Future: fill forms, click buttons, etc."""
        raise NotImplementedError

    def verify(self, url: str, expected: str) -> bool:
        raise NotImplementedError


# ── Basic implementation (DuckDuckGo Lite HTML scrape) ─────────────────────

class BasicWebAgent(WebAgentProvider):
    """
    Minimal web agent: fetches DuckDuckGo Lite results via HTTP.
    No JS, no full browser. Good for v0.1 — upgrade to Playwright/Dejevu for v0.2.
    """

    SEARCH_URL = "https://html.duckduckgo.com/html/"
    TIMEOUT = 10.0

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        try:
            resp = httpx.post(
                self.SEARCH_URL,
                data={"q": query, "kl": "ng-en"},  # ng-en = Nigeria English
                headers={"User-Agent": "NIA-Agent/0.1"},
                timeout=self.TIMEOUT,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            return []

        # Simple regex-style parse (no HTML parser dependency for v0.1)
        import re
        results = []
        # DuckDuckGo Lite result titles are in <a class="result__a"> tags
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        for m in pattern.finditer(resp.text):
            url = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
            if url.startswith("http"):
                results.append(SearchResult(title=title, url=url, snippet=snippet, source="duckduckgo"))
            if len(results) >= num_results:
                break

        # Fallback: if regex got nothing, return a stub result
        if not results:
            results = [SearchResult(
                title=f"Search: {query}",
                url=f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                snippet="Open this link to see full search results.",
                source="duckduckgo",
            )]
        return results

    def browse(self, url: str) -> BrowsedPage:
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": "NIA-Agent/0.1"},
                timeout=self.TIMEOUT,
                follow_redirects=True,
            )
            import re
            title_m = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else url
            # Strip tags and collapse whitespace
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()[:5000]  # Cap at 5000 chars
            return BrowsedPage(url=url, title=title, text=text, status_code=resp.status_code)
        except Exception as exc:
            return BrowsedPage(url=url, title="Error", text=str(exc), status_code=0)

    def extract(self, url: str, selector: str) -> List[str]:
        page = self.browse(url)
        # Very basic: return lines containing the selector string
        return [line.strip() for line in page.text.splitlines() if selector.lower() in line.lower()]

    def verify(self, url: str, expected: str) -> bool:
        page = self.browse(url)
        return expected.lower() in page.text.lower()


# ── Factory ────────────────────────────────────────────────────────────────

def get_web_agent(provider: str = "basic") -> WebAgentProvider:
    if provider == "basic":
        return BasicWebAgent()
    # Future: elif provider == "dejevu": return DejevuWebAgent()
    # Future: elif provider == "playwright": return PlaywrightWebAgent()
    raise ValueError(f"Unknown web agent provider: {provider!r}")
