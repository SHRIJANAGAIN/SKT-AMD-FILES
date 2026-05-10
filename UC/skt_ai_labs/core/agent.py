"""
SKT-AI-LABS Core Agent Framework
Rebranded & Enhanced from Google ADK Patterns
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, TypeVar
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger("skt_ai_labs.core")


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCategory(str, Enum):
    RETRYABLE = "retryable"       # Transient: network timeout, 429, 503
    NON_RETRYABLE = "non_retryable"  # Structural: bad auth, malformed input
    DEGRADED = "degraded"         # Partial failure: 403 paywall, 404


@dataclass
class ToolCall:
    tool_name: str
    input_args: Dict[str, Any]
    output: Any = None
    error: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass 
class AgentRunResult:
    run_id: str
    agent_name: str
    query: str
    answer: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    iterations: int = 0
    total_duration_ms: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    termination_reason: str = "completed"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class AgentConfig(BaseModel):
    """Configuration for all SKT-AI-LABS agents"""

    # Identity
    name: str = "skt_agent"
    description: str = "SKT-AI-LABS Production Agent"

    # Limits
    max_iterations: int = Field(default=15, ge=1, le=100)
    max_concurrent_tools: int = Field(default=10, ge=1, le=50)
    max_run_duration_seconds: float = Field(default=300.0, ge=10)
    token_budget: int = Field(default=128000, ge=1000)

    # Retry
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_exponential_base: float = 2.0

    # LLM
    model: str = "gemini-2.5-pro"
    temperature: float = 0.3
    top_p: float = 0.95
    max_tokens: int = 4096

    # Observability
    log_level: str = "INFO"
    save_intermediate_results: bool = True
    enable_audit_trail: bool = True

    # Streaming
    enable_streaming: bool = False
    stream_chunk_size: int = 100

    class Config:
        env_prefix = "SKT_"


class SKTAgent(ABC):
    """
    Base class for all SKT-AI-LABS agents.

    Features:
    - State management with lifecycle hooks
    - Structured error taxonomy (Retryable/NonRetryable/Degraded)
    - Full audit trail of every tool call
    - Token budget management with intelligent pruning
    - Wall-clock timeout enforcement
    - Loop detection via fingerprinting
    - Concurrent tool execution
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.run_id: Optional[str] = None
        self._history: List[Dict[str, Any]] = []
        self._tool_calls: List[ToolCall] = []
        self._start_time: float = 0.0
        self._token_used: int = 0
        self._loop_fingerprints: set = set()
        self._logger = structlog.get_logger(f"skt_ai_labs.agents.{self.config.name}")

    @property
    def name(self) -> str:
        return self.config.name

    async def run(self, query: str, **kwargs) -> AgentRunResult:
        """
        Main entry point. Executes the agent loop with full guardrails.
        """
        self.run_id = str(uuid.uuid4())
        self._start_time = time.time()
        self.state = AgentState.RUNNING
        self._history = [{"role": "user", "content": query}]
        self._tool_calls = []
        self._token_used = 0
        self._loop_fingerprints = set()

        self._logger.info(
            "agent_run_started",
            run_id=self.run_id,
            query=query[:100],
            max_iterations=self.config.max_iterations,
            max_duration=self.config.max_run_duration_seconds,
        )

        try:
            result = await self._execute_loop(query, **kwargs)
            self.state = AgentState.COMPLETED
            return result

        except Exception as e:
            self.state = AgentState.FAILED
            self._logger.error("agent_run_failed", error=str(e), run_id=self.run_id)
            return AgentRunResult(
                run_id=self.run_id,
                agent_name=self.name,
                query=query,
                answer=f"Agent failed: {str(e)}",
                tool_calls=self._tool_calls,
                iterations=len(self._tool_calls),
                total_duration_ms=(time.time() - self._start_time) * 1000,
                termination_reason="fatal_error",
            )

    async def _execute_loop(self, query: str, **kwargs) -> AgentRunResult:
        """
        Core agent loop with guardrails:
        1. Check wall-clock timeout
        2. Check max iterations
        3. Check token budget (prune if needed)
        4. Call LLM with retry logic
        5. Parse response - if "stop": build report
        6. If "tool_calls": detect loops, execute concurrently, record audit
        7. Repeat
        """
        iteration = 0
        final_answer = ""

        while iteration < self.config.max_iterations:
            # GUARD 1: Wall-clock timeout
            elapsed = time.time() - self._start_time
            if elapsed > self.config.max_run_duration_seconds:
                self._logger.warning("max_duration_exceeded", elapsed=elapsed)
                return self._build_result(final_answer or "Timeout exceeded", "max_duration", iteration)

            # GUARD 2: Token budget
            if self._token_used > self.config.token_budget:
                self._prune_history()

            iteration += 1
            self._logger.info("iteration_started", iteration=iteration, message_count=len(self._history))

            # Step 1: Call LLM
            llm_response = await self._call_llm_with_retry()

            if not llm_response:
                continue

            # Step 2: Check finish reason
            finish_reason = llm_response.get("finish_reason", "stop")

            if finish_reason == "stop":
                final_answer = llm_response.get("content", "")
                self._logger.info("model_finished", iteration=iteration)
                return self._build_result(final_answer, "completed", iteration)

            elif finish_reason == "tool_calls":
                tool_calls_data = llm_response.get("tool_calls", [])

                # Loop detection via fingerprinting
                fingerprint = self._fingerprint_tool_calls(tool_calls_data)
                if fingerprint in self._loop_fingerprints:
                    self._logger.warning("loop_detected", fingerprint=fingerprint)
                    return self._build_result(final_answer or "Loop detected", "loop_detected", iteration)
                self._loop_fingerprints.add(fingerprint)

                # Execute tools concurrently
                results = await self._execute_tools_concurrent(tool_calls_data)

                # Add to history
                self._history.append({
                    "role": "assistant",
                    "tool_calls": tool_calls_data
                })
                for result in results:
                    self._history.append({
                        "role": "tool",
                        "content": str(result.output) if result.error_category != ErrorCategory.DEGRADED else f"Error: {result.error}"
                    })

            else:
                # Unknown finish reason, try to continue
                final_answer = llm_response.get("content", "")

        # Max iterations reached
        return self._build_result(final_answer or "Max iterations reached", "max_iterations", iteration)

    async def _call_llm_with_retry(self) -> Optional[Dict[str, Any]]:
        """Call LLM with exponential backoff retry logic"""
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

        @retry(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(
                multiplier=self.config.retry_base_delay,
                max=self.config.retry_max_delay,
                exp_base=self.config.retry_exponential_base
            ),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True
        )
        async def _call():
            return await self._call_llm()

        try:
            return await _call()
        except Exception as e:
            self._logger.error("llm_call_failed_after_retries", error=str(e))
            return None

    @abstractmethod
    async def _call_llm(self) -> Dict[str, Any]:
        """Implement LLM call in subclass"""
        pass

    @abstractmethod
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        """Implement tool execution in subclass"""
        pass

    async def _execute_tools_concurrent(self, tool_calls_data: List[Dict]) -> List[ToolCall]:
        """Execute multiple tools concurrently with join_all pattern"""
        tasks = []
        for tc in tool_calls_data:
            task = self._execute_tool_with_metrics(tc.get("name"), tc.get("arguments", {}))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for result in results:
            if isinstance(result, Exception):
                tc = ToolCall(
                    tool_name="unknown",
                    input_args={},
                    error=str(result),
                    error_category=ErrorCategory.RETRYABLE,
                )
                processed.append(tc)
                self._tool_calls.append(tc)
            else:
                processed.append(result)
                self._tool_calls.append(result)

        return processed

    async def _execute_tool_with_metrics(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        """Execute single tool with timing and error classification"""
        start = time.time()
        try:
            result = await self._execute_tool(tool_name, args)
            result.duration_ms = (time.time() - start) * 1000

            self._logger.info(
                "tool_call_succeeded",
                tool=tool_name,
                duration_ms=result.duration_ms,
                iteration=len(self._tool_calls),
            )
            return result

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error_msg = str(e)

            # Classify error
            if any(x in error_msg.lower() for x in ["timeout", "429", "503", "connection"]):
                category = ErrorCategory.RETRYABLE
            elif any(x in error_msg.lower() for x in ["403", "401", "paywall", "blocked"]):
                category = ErrorCategory.DEGRADED
            else:
                category = ErrorCategory.NON_RETRYABLE

            self._logger.warning(
                "tool_call_failed",
                tool=tool_name,
                duration_ms=duration_ms,
                category=category.value,
                message=error_msg[:200],
            )

            return ToolCall(
                tool_name=tool_name,
                input_args=args,
                error=error_msg,
                error_category=category,
                duration_ms=duration_ms,
            )

    def _fingerprint_tool_calls(self, tool_calls: List[Dict]) -> str:
        """Create fingerprint for loop detection"""
        import hashlib
        data = str(sorted([(tc.get("name"), str(tc.get("arguments"))) for tc in tool_calls]))
        return hashlib.md5(data.encode()).hexdigest()[:16]

    def _prune_history(self):
        """Intelligent history pruning when token budget exceeded"""
        # Keep system message, first user query, and last N exchanges
        if len(self._history) > 10:
            keep_first = 2  # system + initial query
            keep_last = 8   # recent context
            self._history = self._history[:keep_first] + self._history[-keep_last:]
            self._logger.info("history_pruned", new_length=len(self._history))

    def _build_result(self, answer: str, reason: str, iterations: int) -> AgentRunResult:
        """Build final result with full audit trail"""
        total_duration = (time.time() - self._start_time) * 1000

        successful = sum(1 for tc in self._tool_calls if tc.error is None)
        failed = len(self._tool_calls) - successful

        self._logger.info(
            "agent_run_finished",
            run_id=self.run_id,
            total_ms=total_duration,
            iterations=iterations,
            total_tool_calls=len(self._tool_calls),
            successful=successful,
            failed=failed,
            termination_reason=reason,
        )

        return AgentRunResult(
            run_id=self.run_id or str(uuid.uuid4()),
            agent_name=self.name,
            query=self._history[0]["content"] if self._history else "",
            answer=answer,
            tool_calls=self._tool_calls,
            iterations=iterations,
            total_duration_ms=total_duration,
            token_usage={"input": self._token_used, "output": len(answer)},
            termination_reason=reason,
            metadata={
                "tool_success_rate": successful / len(self._tool_calls) if self._tool_calls else 1.0,
                "failed_tools": [tc.tool_name for tc in self._tool_calls if tc.error],
            }
        )

    async def stream(self, query: str, **kwargs) -> AsyncGenerator[str, None]:
        """Streaming interface for real-time updates"""
        self.state = AgentState.RUNNING

        # Yield initial status
        yield f"data: {{"status": "started", "agent": "{self.name}"}}\n\n"

        result = await self.run(query, **kwargs)

        # Yield final result in chunks
        for i in range(0, len(result.answer), self.config.stream_chunk_size):
            chunk = result.answer[i:i + self.config.stream_chunk_size]
            yield f"data: {{"chunk": "{chunk}", "progress": {i/len(result.answer)*100}}}\n\n"

        yield f"data: {{"status": "completed", "iterations": {result.iterations}}}\n\n"
        self.state = AgentState.COMPLETED
