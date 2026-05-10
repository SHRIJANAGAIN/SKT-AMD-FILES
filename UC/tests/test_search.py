"""
SKT-AI-LABS Search Tool Tests
"""

import pytest
from unittest.mock import Mock, patch

from skt_ai_labs.tools.search.web_search import SKTWebSearch, SearchResult


class TestSKTWebSearch:
    """Test Web Search functionality"""

    def test_init_with_keys(self):
        search = SKTWebSearch(
            tavily_key="test_tavily",
            brave_key="test_brave",
        )
        assert search.tavily_key == "test_tavily"
        assert search.brave_key == "test_brave"

    def test_init_from_env(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "env_tavily")
        search = SKTWebSearch()
        assert search.tavily_key == "env_tavily"

    def test_deduplicate_and_rank(self):
        search = SKTWebSearch()

        results = [
            SearchResult(title="A", url="https://example.com/1", snippet="Test", source="tavily", rank=1),
            SearchResult(title="B", url="https://example.com/1", snippet="Test2", source="brave", rank=1),  # Duplicate URL
            SearchResult(title="C", url="https://example.com/2", snippet="Test3", source="tavily", rank=2),
        ]

        unique = search._deduplicate_and_rank(results, 10)
        assert len(unique) == 2  # One duplicate removed
        assert unique[0].source == "tavily"  # Tavily prioritized

    def test_empty_results(self):
        search = SKTWebSearch()
        unique = search._deduplicate_and_rank([], 5)
        assert len(unique) == 0
