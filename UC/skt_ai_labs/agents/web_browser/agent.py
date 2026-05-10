"""
SKT-AI-LABS Web Browser Agent
Autonomous web navigation and task execution
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import structlog
from langgraph.graph import StateGraph, END

from ...core.agent import SKTAgent, AgentConfig, AgentRunResult, ToolCall
from ...tools.browser.automation import SKTBrowser, BrowserAction
from ...llm.provider import SKTLLMProvider

logger = structlog.get_logger("skt_ai_labs.agents.web_browser")


class BrowserState(dict):
    """LangGraph state for browser agent"""
    task: str
    current_url: str
    actions: List[Dict]
    extracted_data: Dict
    status: str
    error: Optional[str]


class WebBrowserAgent(SKTAgent):
    """
    SKT-AI-LABS Web Browser Agent

    Autonomous web task execution:
    - Navigate to websites
    - Fill forms
    - Extract structured data
    - Click buttons, scroll, interact
    - Multi-page workflows
    - Error recovery

    Can execute natural language tasks like:
    "Go to Amazon, search for 'laptop', filter by 4+ stars, extract top 5 products"
    """

    def __init__(self, 
                 config: Optional[AgentConfig] = None,
                 headless: bool = True,
                 model: str = "gemini-2.5-pro"):

        cfg = config or AgentConfig()
        cfg.name = "skt_web_browser"
        cfg.description = "SKT-AI-LABS Web Browser Agent - Autonomous web navigation"
        cfg.max_iterations = 30  # Browser needs more steps

        super().__init__(cfg)

        self.browser = SKTBrowser(headless=headless, anti_bot=True)
        self.llm = SKTLLMProvider(model=model)
        self._graph = self._build_graph()

    def _build_graph(self):
        """Build browser task execution graph"""
        workflow = StateGraph(BrowserState)

        workflow.add_node("plan", self._node_plan)
        workflow.add_node("execute", self._node_execute)
        workflow.add_node("verify", self._node_verify)
        workflow.add_node("extract", self._node_extract)

        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "execute")
        workflow.add_conditional_edges(
            "execute",
            self._check_status,
            {"verify": "verify", "extract": "extract", "error": END}
        )
        workflow.add_conditional_edges(
            "verify",
            self._should_continue,
            {"plan": "plan", "extract": "extract"}
        )
        workflow.add_edge("extract", END)

        return workflow.compile()

    async def _node_plan(self, state: BrowserState) -> BrowserState:
        """Plan browser actions from task"""
        task = state["task"]
        current_url = state.get("current_url", "")

        plan_prompt = f"""
        You are a web automation expert. Convert the following task into browser actions.

        Current URL: {current_url or "None (starting fresh)"}
        Task: {task}

        Available actions:
        - navigate: Go to URL
        - click: Click element by CSS selector
        - type: Type text into input by selector
        - scroll: Scroll to bottom
        - screenshot: Take screenshot
        - extract: Extract page content
        - wait: Wait for element

        Return JSON array of actions:
        [
            {{"action": "navigate", "url": "https://..."}},
            {{"action": "type", "selector": "#search", "value": "query"}},
            {{"action": "click", "selector": "#submit"}},
            {{"action": "extract"}}
        ]

        Return ONLY valid JSON. No markdown.
        """

        response = await self.llm.generate(plan_prompt, temperature=0.3)

        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                actions = json.loads(json_match.group())
            else:
                actions = json.loads(response)

            state["actions"] = actions
            state["status"] = "planned"
        except:
            state["actions"] = [{"action": "navigate", "url": "https://google.com/search?q=" + task.replace(" ", "+")}]
            state["status"] = "fallback_plan"

        return state

    async def _node_execute(self, state: BrowserState) -> BrowserState:
        """Execute planned browser actions"""
        actions = state.get("actions", [])

        if not actions:
            state["status"] = "error"
            state["error"] = "No actions to execute"
            return state

        # Ensure browser is started
        if not self.browser._page:
            await self.browser.start()

        executed = []
        for action_data in actions:
            try:
                action = BrowserAction(**action_data)
                results = await self.browser.execute_actions([action])
                executed.append({
                    "action": action_data,
                    "result": results[0] if results else None,
                    "success": True,
                })

                # Update current URL after navigation
                if action.action == "navigate" and action.url:
                    state["current_url"] = action.url

                await asyncio.sleep(0.5)  # Rate limiting

            except Exception as e:
                executed.append({
                    "action": action_data,
                    "error": str(e),
                    "success": False,
                })

        state["executed_actions"] = executed
        state["status"] = "executed"

        # Check if any failed
        if any(not e["success"] for e in executed):
            state["status"] = "partial_error"

        return state

    async def _node_verify(self, state: BrowserState) -> BrowserState:
        """Verify execution and decide next steps"""
        executed = state.get("executed_actions", [])
        task = state["task"]

        # Get current page info
        current_url = self.browser._page.url if self.browser._page else ""

        verify_prompt = f"""
        Task: {task}
        Current URL: {current_url}

        Executed actions:
        {json.dumps(executed, indent=2)[:1000]}

        Is the task complete? If not, what additional actions are needed?

        Return JSON:
        {{
            "complete": true/false,
            "additional_actions": [{{"action": "...", ...}}],
            "reason": "..."
        }}
        """

        response = await self.llm.generate(verify_prompt, temperature=0.3)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                verification = json.loads(json_match.group())
            else:
                verification = json.loads(response)

            if verification.get("complete"):
                state["status"] = "complete"
            else:
                state["actions"] = verification.get("additional_actions", [])
                state["status"] = "needs_more"

        except:
            state["status"] = "complete"  # Default to complete on parse error

        return state

    async def _node_extract(self, state: BrowserState) -> BrowserState:
        """Extract final data from page"""
        try:
            data = await self.browser.extract_content()
            state["extracted_data"] = {
                "url": data.url,
                "title": data.title,
                "content": data.content[:3000],
                "links": data.links[:20],
                "metadata": data.metadata,
            }
            state["status"] = "extracted"
        except Exception as e:
            state["extracted_data"] = {"error": str(e)}
            state["status"] = "extract_error"

        return state

    def _check_status(self, state: BrowserState) -> str:
        """Route based on execution status"""
        status = state.get("status", "")
        if status == "error":
            return "error"
        elif status in ["complete", "extracted"]:
            return "extract"
        else:
            return "verify"

    def _should_continue(self, state: BrowserState) -> str:
        """Decide whether to continue or finish"""
        if state.get("status") == "needs_more" and state.get("iterations", 0) < self.config.max_iterations:
            return "plan"
        return "extract"

    async def execute(self, task: str, **kwargs) -> AgentRunResult:
        """
        Execute a web browsing task.

        Args:
            task: Natural language description of web task

        Returns:
            AgentRunResult with extracted data
        """
        initial_state = BrowserState(
            task=task,
            current_url="",
            actions=[],
            extracted_data={},
            status="start",
            error=None,
        )

        try:
            final_state = await self._graph.ainvoke(initial_state)

            # Build human-readable result
            data = final_state.get("extracted_data", {})
            answer = self._format_result(data, task)

            return AgentRunResult(
                run_id=self.run_id or "browser_run",
                agent_name=self.name,
                query=task,
                answer=answer,
                tool_calls=[],
                iterations=0,
                total_duration_ms=0,
                token_usage={},
                termination_reason="completed",
                metadata={
                    "extracted_data": data,
                    "final_url": data.get("url", ""),
                    "actions_executed": len(final_state.get("executed_actions", [])),
                }
            )

        finally:
            await self.browser.close()

    def _format_result(self, data: Dict, task: str) -> str:
        """Format extracted data as readable response"""
        if data.get("error"):
            return f"Error executing task: {data['error']}"

        parts = [
            f"## Task: {task}",
            f"**URL:** {data.get('url', 'N/A')}",
            f"**Title:** {data.get('title', 'N/A')}",
            "",
            "### Content:",
            data.get('content', 'No content extracted')[:2000],
            "",
            "### Links Found:",
        ]

        for link in data.get('links', [])[:10]:
            text = link.get('text', '')[:50]
            url = link.get('href', '')
            parts.append(f"- [{text}]({url})")

        return "
".join(parts)

    async def _call_llm(self) -> Dict[str, Any]:
        return {"finish_reason": "stop", "content": ""}

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        return ToolCall(tool_name=tool_name, input_args=args)
