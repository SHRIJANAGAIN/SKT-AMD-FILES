"""
SKT-AI-LABS Multi-Agent Supervisor
Manages teams of agents with intelligent routing
"""

import asyncio
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass
from enum import Enum

import structlog
from pydantic import BaseModel

from .agent import SKTAgent, AgentConfig, AgentRunResult

logger = structlog.get_logger("skt_ai_labs.supervisor")


class RoutingStrategy(str, Enum):
    SEQUENTIAL = "sequential"      # One after another
    PARALLEL = "parallel"        # All at once, merge results
    ADAPTIVE = "adaptive"        # LLM decides routing
    HIERARCHICAL = "hierarchical"  # Tree structure


class AgentCapability(BaseModel):
    """Defines what an agent can do"""
    name: str
    description: str
    tools: List[str] = []
    max_tokens: int = 4096
    strengths: List[str] = []  # e.g., ["research", "coding", "analysis"]


@dataclass
class TaskAssignment:
    agent_name: str
    task_description: str
    priority: int = 1
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class SKTSupervisor:
    """
    Intelligent supervisor that routes tasks to the best agent.

    Features:
    - Automatic task decomposition
    - Agent capability matching
    - Dependency resolution
    - Result aggregation
    - Conflict resolution
    """

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ADAPTIVE):
        self.strategy = strategy
        self.agents: Dict[str, SKTAgent] = {}
        self.capabilities: Dict[str, AgentCapability] = {}
        self._logger = logger

    def register_agent(self, name: str, agent: SKTAgent, capabilities: AgentCapability):
        """Register an agent with its capabilities"""
        self.agents[name] = agent
        self.capabilities[name] = capabilities
        self._logger.info("agent_registered", name=name, tools=capabilities.tools)

    async def route(self, query: str, context: Optional[Dict] = None) -> Dict[str, AgentRunResult]:
        """
        Route query to appropriate agent(s) based on strategy.
        """
        if self.strategy == RoutingStrategy.SEQUENTIAL:
            return await self._route_sequential(query, context)
        elif self.strategy == RoutingStrategy.PARALLEL:
            return await self._route_parallel(query, context)
        elif self.strategy == RoutingStrategy.ADAPTIVE:
            return await self._route_adaptive(query, context)
        else:
            return await self._route_hierarchical(query, context)

    async def _route_adaptive(self, query: str, context: Optional[Dict]) -> Dict[str, AgentRunResult]:
        """
        Adaptive routing: Analyze query and assign to best agent(s).
        Uses LLM to decide decomposition and routing.
        """
        # Step 1: Analyze query to determine needed capabilities
        needed_capabilities = await self._analyze_query(query)

        # Step 2: Match agents to capabilities
        assignments = self._match_agents(needed_capabilities)

        # Step 3: Execute with dependency resolution
        results = await self._execute_with_dependencies(assignments, query, context)

        # Step 4: Merge and synthesize
        return await self._synthesize_results(results, query)

    async def _analyze_query(self, query: str) -> List[str]:
        """Analyze what capabilities are needed for this query"""
        # In production, this uses an LLM to classify
        # For hackathon: keyword-based matching
        capabilities_needed = []

        keywords = {
            "research": ["research", "find", "search", "investigate", "latest", "news"],
            "browser": ["website", "browse", "click", "navigate", "scrape", "extract"],
            "rag": ["document", "knowledge", "file", "pdf", "database", "previous"],
            "code": ["code", "program", "function", "script", "debug"],
            "analysis": ["analyze", "compare", "evaluate", "assess"],
        }

        query_lower = query.lower()
        for cap, words in keywords.items():
            if any(w in query_lower for w in words):
                capabilities_needed.append(cap)

        if not capabilities_needed:
            capabilities_needed = ["research"]  # Default

        return capabilities_needed

    def _match_agents(self, capabilities: List[str]) -> List[TaskAssignment]:
        """Match required capabilities to registered agents"""
        assignments = []

        for cap in capabilities:
            best_agent = None
            best_score = 0

            for name, cap_obj in self.capabilities.items():
                score = sum(1 for s in cap_obj.strengths if cap in s.lower())
                if cap in cap_obj.description.lower():
                    score += 2
                if score > best_score:
                    best_score = score
                    best_agent = name

            if best_agent:
                assignments.append(TaskAssignment(
                    agent_name=best_agent,
                    task_description=f"Handle {cap} aspect of query",
                    priority=1
                ))

        return assignments

    async def _execute_with_dependencies(
        self, 
        assignments: List[TaskAssignment], 
        query: str,
        context: Optional[Dict]
    ) -> Dict[str, AgentRunResult]:
        """Execute tasks respecting dependencies"""
        results = {}
        completed = set()

        while len(completed) < len(assignments):
            # Find tasks with no unmet dependencies
            ready = [
                a for a in assignments 
                if a.agent_name not in completed 
                and all(d in completed for d in a.dependencies)
            ]

            if not ready:
                break  # Circular dependency or all done

            # Execute ready tasks in parallel
            tasks = []
            for assignment in ready:
                agent = self.agents[assignment.agent_name]
                task_query = f"{assignment.task_description}: {query}"
                tasks.append(agent.run(task_query, **(context or {})))

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for assignment, result in zip(ready, batch_results):
                if isinstance(result, Exception):
                    self._logger.error("agent_failed", agent=assignment.agent_name, error=str(result))
                    # Create error result
                    from .agent import AgentRunResult
                    results[assignment.agent_name] = AgentRunResult(
                        run_id="error",
                        agent_name=assignment.agent_name,
                        query=query,
                        answer=f"Error: {str(result)}",
                        termination_reason="error",
                    )
                else:
                    results[assignment.agent_name] = result

                completed.add(assignment.agent_name)

        return results

    async def _synthesize_results(
        self, 
        results: Dict[str, AgentRunResult], 
        query: str
    ) -> Dict[str, AgentRunResult]:
        """Merge results from multiple agents into coherent response"""
        # Add synthesis metadata
        for name, result in results.items():
            result.metadata["synthesized"] = True
            result.metadata["team_size"] = len(results)

        self._logger.info(
            "supervisor_synthesis_complete",
            agents=list(results.keys()),
            total_iterations=sum(r.iterations for r in results.values()),
        )

        return results

    async def _route_sequential(self, query: str, context: Optional[Dict]) -> Dict[str, AgentRunResult]:
        """Execute agents one after another, passing context forward"""
        results = {}
        accumulated_context = context or {}

        for name, agent in self.agents.items():
            result = await agent.run(query, **accumulated_context)
            results[name] = result
            accumulated_context["previous_result"] = result.answer

        return results

    async def _route_parallel(self, query: str, context: Optional[Dict]) -> Dict[str, AgentRunResult]:
        """Execute all agents simultaneously"""
        tasks = [agent.run(query, **(context or {})) for agent in self.agents.values()]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for name, result in zip(self.agents.keys(), results_list):
            if isinstance(result, Exception):
                from .agent import AgentRunResult
                results[name] = AgentRunResult(
                    run_id="error", agent_name=name, query=query,
                    answer=f"Error: {str(result)}", termination_reason="error",
                )
            else:
                results[name] = result

        return results

    async def _route_hierarchical(self, query: str, context: Optional[Dict]) -> Dict[str, AgentRunResult]:
        """Tree-structured execution with manager agents"""
        # For hackathon: simplified version
        return await self._route_adaptive(query, context)


class MultiAgentTeam:
    """
    High-level interface for multi-agent teams.

    Usage:
        team = MultiAgentTeam(
            agents={"researcher": DeepResearchAgent(), "browser": WebBrowserAgent()},
            supervisor=SKTSupervisor(strategy="adaptive")
        )
        result = await team.execute("Research latest AI trends and browse specific sites")
    """

    def __init__(self, agents: Dict[str, SKTAgent], supervisor: Optional[SKTSupervisor] = None):
        self.supervisor = supervisor or SKTSupervisor(strategy=RoutingStrategy.ADAPTIVE)

        for name, agent in agents.items():
            cap = AgentCapability(
                name=name,
                description=agent.config.description,
                tools=[],  # Would be populated from agent tools
                strengths=[name.lower().replace("agent", "")],
            )
            self.supervisor.register_agent(name, agent, cap)

    async def execute(self, query: str, **kwargs) -> Dict[str, AgentRunResult]:
        """Execute query across the team"""
        return await self.supervisor.route(query, kwargs)

    def add_agent(self, name: str, agent: SKTAgent, capabilities: AgentCapability):
        """Add agent to team dynamically"""
        self.supervisor.register_agent(name, agent, capabilities)
