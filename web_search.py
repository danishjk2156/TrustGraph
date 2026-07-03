"""Small web-search helpers for TrustGraph verification."""

from __future__ import annotations

import asyncio
import json
import os
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


SearchResult = dict[str, str]


async def search_web(query: str, limit: int = 3) -> list[SearchResult]:
    """Return compact web search results using Tavily or DuckDuckGo HTML."""

    query = query.strip()
    if not query:
        return []

    return await asyncio.to_thread(_search_web_sync, query, limit)


def _search_web_sync(query: str, limit: int) -> list[SearchResult]:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        results = _search_tavily(query, tavily_key, limit)
        if results:
            return results
    return _search_duckduckgo(query, limit)


def _search_tavily(query: str, api_key: str, limit: int) -> list[SearchResult]:
    payload = json.dumps(
        {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "include_answer": False,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return []

    return [
        _clean_result(
            title=item.get("title", ""),
            snippet=item.get("content", ""),
            url=item.get("url", ""),
        )
        for item in data.get("results", [])[:limit]
        if item.get("url")
    ]


def _search_duckduckgo(query: str, limit: int) -> list[SearchResult]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    parser = _DuckDuckGoParser(limit=limit)
    parser.feed(html)
    return parser.results


def _clean_result(title: str, snippet: str, url: str) -> SearchResult:
    return {
        "title": " ".join(unescape(title).split()),
        "snippet": " ".join(unescape(snippet).split()),
        "url": _unwrap_duckduckgo_url(unescape(url).strip()),
    }


def _unwrap_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    return url


class _DuckDuckGoParser(HTMLParser):
    def __init__(self, limit: int) -> None:
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.results: list[SearchResult] = []
        self._current: dict[str, Any] | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = set(attr.get("class", "").split())

        if tag == "a" and "result__a" in classes:
            self._current = {"title": [], "snippet": [], "url": attr.get("href", "")}
            self._capture = "title"
        elif self._current is not None and "result__snippet" in classes:
            self._capture = "snippet"

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture:
            self._current[self._capture].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == "a" and self._capture == "title":
            self._capture = None
        elif tag in {"a", "div"} and self._capture == "snippet":
            self._capture = None
            result = _clean_result(
                title=" ".join(self._current["title"]),
                snippet=" ".join(self._current["snippet"]),
                url=self._current["url"],
            )
            if result["title"] and result["url"]:
                self.results.append(result)
            self._current = None
            if len(self.results) >= self.limit:
                self._capture = None
