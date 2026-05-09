"""
SKT-AI-LABS Deep Research Agent
Multi-step reasoning with recursive exploration
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import structlog
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from ...core.agent import SKTAgent, AgentConfig, AgentRunResult, ToolCall, ErrorCategory
from ...tools.search.web_search import SKTWebSearch
from ...tools.browser.automation import SKTBrowser
from ...tools.scraper.intelligent_scraper import IntelligentScraper
from ...llm.provider import SKTLLMProvider

logger = structlog.get_logger("skt_ai_labs.agents.deep_research")


class DeepResearchState(dict):
    """LangGraph state for deep research"""
    query: str
    iterations: int
    search_queries: List[str]
    search_results: List[Dict]
    scraped_content: List[Dict]
    analysis: str
    report: str
    next_step: str
    errors: List[str]


class DeepResearchAgent(SKTAgent):
    """
    SKT-AI-LABS Deep Research Agent

    Capabilities:
    - Recursive multi-query search
    - Intelligent URL prioritization
    - Concurrent content scraping
    - Multi-source synthesis
    - Citation tracking
    - Confidence scoring
    - Structured markdown output

    Inspired by Google Deep Research but fully independent implementation.
    """

    def __init__(self, 
                 config: Optional[AgentConfig] = None,
                 search_provider: str = "auto",
                 model: str = "gemini-2.5-pro"):

        cfg = config or AgentConfig()
        cfg.name = "skt_deep_research"
        cfg.description = "SKT-AI-LABS Deep Research Agent - Multi-step web research with synthesis"
        cfg.model = model
        cfg.max_iterations = 20

        super().__init__(cfg)

        self.search_provider = search_provider
        self.llm = SKTLLMProvider(model=model)
        self.search_tool = SKTWebSearch()
        self.browser = SKTBrowser(headless=True, anti_bot=True)
        self.scraper = IntelligentScraper()

        # Build LangGraph
        self._graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph workflow for deep research"""
        workflow = StateGraph(DeepResearchState)

        # Define nodes
        workflow.add_node("plan", self._node_plan)
        workflow.add_node("search", self._node_search)
        workflow.add_node("scrape", self._node_scrape)
        workflow.add_node("analyze", self._node_analyze)
        workflow.add_node("synthesize", self._node_synthesize)

        # Define edges
        workflow.set_entry_point("plan")
        workflow.add_conditional_edges(
            "plan",
            self._should_continue,
            {"search": "search", "synthesize": "synthesize"}
        )
        workflow.add_edge("search", "scrape")
        workflow.add_edge("scrape", "analyze")
        workflow.add_conditional_edges(
            "analyze",
            self._should_continue,
            {"search": "search", "synthesize": "synthesize"}
        )
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def _node_plan(self, state: DeepResearchState) -> DeepResearchState:
        """Plan search strategy based on query"""
        query = state["query"]

        planning_prompt = f"""
        You are a research planning expert. Given the user query, create a search strategy.

        Query: {query}

        Generate:
        1. 3-5 specific search queries to gather comprehensive information
        2. Key aspects to investigate
        3. Types of sources to prioritize (academic, news, official, etc.)

        Return ONLY a JSON object:
        {{
            "search_queries": ["query1", "query2", ...],
            "key_aspects": ["aspect1", "aspect2", ...],
            "source_priority": ["type1", "type2", ...]
        }}
        """

        response = await self.llm.generate(planning_prompt, temperature=0.3)

        try:
            plan = json.loads(response)
            state["search_queries"] = plan.get("search_queries", [query])
            state["key_aspects"] = plan.get("key_aspects", [])
            state["next_step"] = "search"
        except:
            state["search_queries"] = [query]
            state["next_step"] = "search"

        state["iterations"] = state.get("iterations", 0) + 1
        return state

    async def _node_search(self, state: DeepResearchState) -> DeepResearchState:
        """Execute searches concurrently"""
        queries = state["search_queries"]

        async with self.search_tool:
            results = await self.search_tool.search_multiple(queries, num_results=5, search_depth="deep")

        all_results = []
        for q, res in results.items():
            for r in res:
                all_results.append({
                    "query": q,
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                })

        state["search_results"] = all_results
        state["next_step"] = "scrape"

        self._logger.info("search_complete", queries=len(queries), results=len(all_results))
        return state

    async def _node_scrape(self, state: DeepResearchState) -> DeepResearchState:
        """Scrape content from top results concurrently"""
        results = state["search_results"]

        # Prioritize and deduplicate URLs
        urls = []
        seen = set()
        for r in results:
            url = r["url"]
            if url not in seen and len(urls) < 10:  # Max 10 pages
                seen.add(url)
                urls.append(url)

        # Scrape concurrently
        scraped = []
        await self.browser.start()

        try:
            tasks = [self._scrape_single(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    self._logger.warning("scrape_failed", url=url, error=str(result)[:100])
                    scraped.append({"url": url, "error": str(result), "content": ""})
                else:
                    scraped.append(result)

        finally:
            await self.browser.close()

        state["scraped_content"] = scraped
        state["next_step"] = "analyze"

        self._logger.info("scrape_complete", pages=len(scraped))
        return state

    async def _scrape_single(self, url: str) -> Dict:
        """Scrape single URL with retry"""
        for attempt in range(2):
            try:
                data = await self.browser.extract_content(url)
                return {
                    "url": url,
                    "title": data.title,
                    "content": data.content[:5000],  # Limit content
                    "metadata": data.metadata,
                    "links": len(data.links),
                }
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(2)
                else:
                    raise

    async def _node_analyze(self, state: DeepResearchState) -> DeepResearchState:
        """Analyze scraped content and decide next steps"""
        scraped = state["scraped_content"]
        query = state["query"]

        # Filter out errors
        valid_content = [s for s in scraped if not s.get("error")]

        if not valid_content:
            state["next_step"] = "synthesize"
            return state

        # Build analysis prompt
        content_summary = "\n\n".join([
            f"Source: {s['url']}\nTitle: {s['title']}\nContent: {s['content'][:1000]}"
            for s in valid_content[:5]
        ])

        analysis_prompt = f"""
        Analyze the following research content for query: {query}

        {content_summary}

        Determine:
        1. What information gaps remain?
        2. What follow-up searches are needed?
        3. Is the information sufficient to answer the query?

        Return JSON:
        {{
            "sufficient": true/false,
            "gaps": ["gap1", "gap2"],
            "follow_up_queries": ["query1", "query2"],
            "key_findings": ["finding1", "finding2"]
        }}
        """

        response = await self.llm.generate(analysis_prompt, temperature=0.3)

        try:
            analysis = json.loads(response)
            if analysis.get("sufficient") or state["iterations"] >= self.config.max_iterations:
                state["next_step"] = "synthesize"
            else:
                state["search_queries"] = analysis.get("follow_up_queries", [])
                state["next_step"] = "search"

            state["analysis"] = json.dumps(analysis)
        except:
            state["next_step"] = "synthesize"

        return state

    async def _node_synthesize(self, state: DeepResearchState) -> DeepResearchState:
        """Generate final research report"""
        scraped = state["scraped_content"]
        query = state["query"]

        valid_content = [s for s in scraped if not s.get("error")]

        synthesis_prompt = f"""
        Generate a comprehensive research report for: {query}

        Based on the following sources:

        {self._format_sources(valid_content)}

        Requirements:
        1. Executive summary (2-3 paragraphs)
        2. Key findings with bullet points
        3. Detailed analysis sections
        4. All claims must have [Source: URL] citations
        5. Confidence score (High/Medium/Low) based on source quality
        6. Limitations and gaps
        7. Suggestions for further research

        Format as clean Markdown.
        """

        report = await self.llm.generate(synthesis_prompt, temperature=0.4, max_tokens=4000)

        state["report"] = report
        state["next_step"] = "done"
        return state

    def _should_continue(self, state: DeepResearchState) -> str:
        """Decide whether to continue or synthesize"""
        if state.get("next_step") == "synthesize":
            return "synthesize"
        if state["iterations"] >= self.config.max_iterations:
            return "synthesize"
        return "search"

    def _format_sources(self, sources: List[Dict]) -> str:
        """Format sources for prompt"""
        return "\n\n".join([
            f"[{i+1}] {s['title']}\nURL: {s['url']}\n{s['content'][:800]}"
            for i, s in enumerate(sources)
        ])

    async def research(self, query: str, **kwargs) -> AgentRunResult:
        """Main entry point for deep research"""
        initial_state = DeepResearchState(
            query=query,
            iterations=0,
            search_queries=[],
            search_results=[],
            scraped_content=[],
            analysis="",
            report="",
            next_step="plan",
            errors=[],
        )

        # Run LangGraph
        final_state = await self._graph.ainvoke(initial_state)

        # Build result
        return AgentRunResult(
            run_id=self.run_id or "research_run",
            agent_name=self.name,
            query=query,
            answer=final_state.get("report", ""),
            tool_calls=self._tool_calls,
            iterations=final_state.get("iterations", 0),
            total_duration_ms=(time.time() - self._start_time) * 1000 if self._start_time else 0,
            token_usage={},
            termination_reason="completed",
            metadata={
                "sources": [s["url"] for s in final_state.get("scraped_content", []) if not s.get("error")],
                "search_queries_executed": len(final_state.get("search_results", [])),
            }
        )

    async def _call_llm(self) -> Dict[str, Any]:
        """Required by base class - not used in graph mode"""
        return {"finish_reason": "stop", "content": ""}

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        """Required by base class - not used in graph mode"""
        return ToolCall(tool_name=tool_name, input_args=args)
