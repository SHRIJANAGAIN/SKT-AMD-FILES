"""
SKT-AI-LABS Core Tests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from skt_ai_labs.core.agent import SKTAgent, AgentConfig, AgentRunResult, ErrorCategory, ToolCall
from skt_ai_labs.core.supervisor import SKTSupervisor, MultiAgentTeam, RoutingStrategy


class MockAgent(SKTAgent):
    """Mock agent for testing"""

    async def _call_llm(self):
        return {"finish_reason": "stop", "content": "Mock response"}

    async def _execute_tool(self, tool_name, args):
        return ToolCall(tool_name=tool_name, input_args=args, output="mock_output")


class TestAgentConfig:
    """Test AgentConfig"""

    def test_default_config(self):
        config = AgentConfig()
        assert config.name == "skt_agent"
        assert config.max_iterations == 15
        assert config.token_budget == 128000

    def test_custom_config(self):
        config = AgentConfig(name="custom", max_iterations=5)
        assert config.name == "custom"
        assert config.max_iterations == 5


class TestSKTAgent:
    """Test SKTAgent base class"""

    @pytest.mark.asyncio
    async def test_run_completion(self):
        agent = MockAgent()
        result = await agent.run("Test query")

        assert isinstance(result, AgentRunResult)
        assert result.query == "Test query"
        assert result.termination_reason == "completed"
        assert result.agent_name == "skt_agent"

    @pytest.mark.asyncio
    async def test_error_taxonomy(self):
        """Test error classification"""
        agent = MockAgent()

        # Test retryable error detection
        retryable_errors = ["timeout", "429", "503", "connection"]
        for err in retryable_errors:
            assert any(x in err for x in ["timeout", "429", "503", "connection"])

        # Test degraded error detection
        degraded_errors = ["403", "401", "paywall", "blocked"]
        for err in degraded_errors:
            assert any(x in err for x in ["403", "401", "paywall", "blocked"])


class TestSKTSupervisor:
    """Test Supervisor"""

    @pytest.mark.asyncio
    async def test_agent_registration(self):
        supervisor = SKTSupervisor(strategy=RoutingStrategy.ADAPTIVE)
        agent = MockAgent()

        from skt_ai_labs.core.supervisor import AgentCapability
        cap = AgentCapability(name="test", description="Test agent", tools=[], strengths=["test"])

        supervisor.register_agent("test_agent", agent, cap)
        assert "test_agent" in supervisor.agents

    @pytest.mark.asyncio
    async def test_query_analysis(self):
        supervisor = SKTSupervisor()

        # Test research keywords
        caps = await supervisor._analyze_query("Research latest AI trends")
        assert "research" in caps

        # Test browser keywords
        caps = await supervisor._analyze_query("Browse website and extract data")
        assert "browser" in caps

        # Test RAG keywords
        caps = await supervisor._analyze_query("Search documents for information")
        assert "rag" in caps


class TestMultiAgentTeam:
    """Test MultiAgentTeam"""

    @pytest.mark.asyncio
    async def test_team_execution(self):
        agent1 = MockAgent()
        agent2 = MockAgent()

        team = MultiAgentTeam(
            agents={"agent1": agent1, "agent2": agent2},
            supervisor=SKTSupervisor(strategy=RoutingStrategy.SEQUENTIAL)
        )

        results = await team.execute("Test query")
        assert len(results) == 2
        assert "agent1" in results
        assert "agent2" in results
