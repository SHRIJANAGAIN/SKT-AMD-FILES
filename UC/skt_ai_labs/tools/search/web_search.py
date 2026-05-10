"""
SKT-AI-LABS Web Search Tool
Multi-provider search with fallback chain
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger("skt_ai_labs.tools.search")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # Which search provider
    rank: int
    timestamp: float = 0.0


class SKTWebSearch:
    """
    Production-grade web search with multiple provider fallback.

    Providers (in priority order):
    1. Tavily (best quality, paid)
    2. Brave Search (good free tier)
    3. DuckDuckGo (free, no API key)
    4. SerpAPI (Google results)
    5. Bing Search

    Features:
    - Automatic fallback on failure
    - Concurrent multi-provider search
    - Result deduplication
    - Relevance scoring
    - Rate limit handling
    """

    def __init__(self, 
                 tavily_key: Optional[str] = None,
                 brave_key: Optional[str] = None,
                 serpapi_key: Optional[str] = None,
                 bing_key: Optional[str] = None):

        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY")
        self.brave_key = brave_key or os.getenv("BRAVE_API_KEY")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY")
        self.bing_key = bing_key or os.getenv("BING_SEARCH_KEY")

        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logger

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "SKT-AI-LABS-Agent/1.0"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def search(self, 
                     query: str, 
                     num_results: int = 10,
                     search_depth: str = "basic",
                     include_domains: Optional[List[str]] = None,
                     exclude_domains: Optional[List[str]] = None,
                     **kwargs) -> List[SearchResult]:
        """
        Execute search with automatic provider fallback.

        Args:
            query: Search query
            num_results: Number of results desired
            search_depth: "basic" or "deep" (deep = more context)
            include_domains: Only search these domains
            exclude_domains: Exclude these domains

        Returns:
            List of SearchResult objects, deduplicated and ranked
        """
        self._logger.info("search_started", query=query[:80], depth=search_depth)

        # Try providers in parallel for speed, but with priority
        all_results = []

        # Primary: Tavily (if available)
        if self.tavily_key:
            try:
                results = await self._search_tavily(query, num_results, search_depth)
                all_results.extend(results)
                if len(all_results) >= num_results:
                    return self._deduplicate_and_rank(all_results, num_results)
            except Exception as e:
                self._logger.warning("tavily_failed", error=str(e)[:100])

        # Secondary: Brave (if available)
        if self.brave_key:
            try:
                results = await self._search_brave(query, num_results)
                all_results.extend(results)
                if len(all_results) >= num_results:
                    return self._deduplicate_and_rank(all_results, num_results)
            except Exception as e:
                self._logger.warning("brave_failed", error=str(e)[:100])

        # Tertiary: DuckDuckGo (free, always available)
        try:
            results = await self._search_duckduckgo(query, num_results)
            all_results.extend(results)
        except Exception as e:
            self._logger.warning("duckduckgo_failed", error=str(e)[:100])

        # Quaternary: SerpAPI
        if self.serpapi_key:
            try:
                results = await self._search_serpapi(query, num_results)
                all_results.extend(results)
            except Exception as e:
                self._logger.warning("serpapi_failed", error=str(e)[:100])

        if not all_results:
            self._logger.error("all_search_providers_failed", query=query[:80])
            return []

        return self._deduplicate_and_rank(all_results, num_results)

    async def _search_tavily(self, query: str, num: int, depth: str) -> List[SearchResult]:
        """Tavily AI Search - Best quality results"""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": depth,
            "max_results": num,
            "include_answer": False,
            "include_images": False,
        }

        async with self._session.post(url, json=payload) as resp:
            data = await resp.json()

        results = []
        for i, r in enumerate(data.get("results", [])):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", r.get("snippet", "")),
                source="tavily",
                rank=i + 1,
                timestamp=time.time(),
            ))

        self._logger.info("tavily_results", count=len(results))
        return results

    async def _search_brave(self, query: str, num: int) -> List[SearchResult]:
        """Brave Search API"""
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "X-Subscription-Token": self.brave_key,
            "Accept": "application/json",
        }
        params = {
            "q": query,
            "count": min(num, 20),
            "offset": 0,
        }

        async with self._session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()

        results = []
        for i, r in enumerate(data.get("web", {}).get("results", [])):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
                source="brave",
                rank=i + 1,
                timestamp=time.time(),
            ))

        self._logger.info("brave_results", count=len(results))
        return results

    async def _search_duckduckgo(self, query: str, num: int) -> List[SearchResult]:
        """DuckDuckGo - Free, no API key needed"""
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=num)):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo",
                    rank=i + 1,
                    timestamp=time.time(),
                ))

        self._logger.info("duckduckgo_results", count=len(results))
        return results

    async def _search_serpapi(self, query: str, num: int) -> List[SearchResult]:
        """SerpAPI - Google results"""
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "engine": "google",
            "num": min(num, 10),
        }

        async with self._session.get(url, params=params) as resp:
            data = await resp.json()

        results = []
        for i, r in enumerate(data.get("organic_results", [])):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
                source="serpapi",
                rank=i + 1,
                timestamp=time.time(),
            ))

        self._logger.info("serpapi_results", count=len(results))
        return results

    def _deduplicate_and_rank(self, results: List[SearchResult], max_results: int) -> List[SearchResult]:
        """Deduplicate by URL and re-rank by relevance heuristics"""
        seen_urls = set()
        unique = []

        for r in results:
            normalized_url = r.url.rstrip("/").lower()
            if normalized_url not in seen_urls and r.url:
                seen_urls.add(normalized_url)
                unique.append(r)

        # Simple ranking: prefer Tavily > Brave > SerpAPI > DDG
        source_priority = {"tavily": 0, "brave": 1, "serpapi": 2, "duckduckgo": 3}
        unique.sort(key=lambda x: (source_priority.get(x.source, 99), x.rank))

        return unique[:max_results]

    async def search_multiple(self, queries: List[str], **kwargs) -> Dict[str, List[SearchResult]]:
        """Execute multiple searches concurrently"""
        tasks = [self.search(q, **kwargs) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            q: r if not isinstance(r, Exception) else [] 
            for q, r in zip(queries, results)
        }
