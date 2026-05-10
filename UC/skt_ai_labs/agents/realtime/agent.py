"""
SKT-AI-LABS Real-time Agent
Live streaming data processing and analysis
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

import structlog
import websockets

from ...core.agent import SKTAgent, AgentConfig, AgentRunResult, ToolCall
from ...llm.provider import SKTLLMProvider

logger = structlog.get_logger("skt_ai_labs.agents.realtime")


class RealtimeAgent(SKTAgent):
    """
    SKT-AI-LABS Real-time Agent

    Processes live data streams:
    - WebSocket data feeds
    - Live APIs (stock prices, news, social media)
    - IoT sensor data
    - Real-time analysis and alerting

    Features:
    - Async streaming processing
    - Sliding window analysis
    - Pattern detection
    - Automatic summarization
    - Alert generation
    """

    def __init__(self,
                 config: Optional[AgentConfig] = None,
                 model: str = "gemini-2.5-flash",  # Fast model for real-time
                 window_size: int = 10):

        cfg = config or AgentConfig()
        cfg.name = "skt_realtime"
        cfg.description = "SKT-AI-LABS Real-time Streaming Agent"
        cfg.max_iterations = 1000  # Continuous

        super().__init__(cfg)

        self.llm = SKTLLMProvider(model=model)
        self.window_size = window_size
        self._buffer: List[Dict] = []
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        self._handlers[event_type] = handler

    async def process_stream(self, 
                            source: str,
                            stream_type: str = "websocket",
                            **kwargs) -> AsyncGenerator[Dict, None]:
        """
        Process a live data stream.

        Args:
            source: URL or connection string
            stream_type: "websocket", "sse", "polling"

        Yields:
            Analysis results
        """
        self._running = True

        if stream_type == "websocket":
            async for result in self._process_websocket(source, **kwargs):
                yield result
        elif stream_type == "sse":
            async for result in self._process_sse(source, **kwargs):
                yield result
        else:
            async for result in self._process_polling(source, **kwargs):
                yield result

    async def _process_websocket(self, url: str, **kwargs) -> AsyncGenerator[Dict, None]:
        """Process WebSocket stream"""
        try:
            async with websockets.connect(url) as ws:
                while self._running:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(message)

                        result = await self._analyze_chunk(data)
                        if result:
                            yield result

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        logger.warning("invalid_json", message=message[:100])
                        continue

        except Exception as e:
            logger.error("websocket_error", error=str(e))
            yield {"error": str(e), "status": "disconnected"}

    async def _process_sse(self, url: str, **kwargs) -> AsyncGenerator[Dict, None]:
        """Process Server-Sent Events"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                async for line in response.content:
                    if line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            result = await self._analyze_chunk(data)
                            if result:
                                yield result
                        except:
                            pass

    async def _process_polling(self, url: str, interval: float = 5.0, **kwargs) -> AsyncGenerator[Dict, None]:
        """Process via polling"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    async with session.get(url) as response:
                        data = await response.json()
                        result = await self._analyze_chunk(data)
                        if result:
                            yield result
                except Exception as e:
                    logger.warning("poll_error", error=str(e))

                await asyncio.sleep(interval)

    async def _analyze_chunk(self, data: Dict) -> Optional[Dict]:
        """Analyze a single data chunk"""
        self._buffer.append({
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep only window_size recent items
        if len(self._buffer) > self.window_size:
            self._buffer.pop(0)

        # Analyze when buffer is full
        if len(self._buffer) >= self.window_size:
            return await self._analyze_window()

        return None

    async def _analyze_window(self) -> Dict:
        """Analyze current window of data"""
        # Build context from buffer
        context = json.dumps([b["data"] for b in self._buffer], indent=2)[:2000]

        prompt = f"""
        Analyze the following real-time data window:

        {context}

        Provide:
        1. Key patterns or anomalies
        2. Trend summary
        3. Notable events
        4. Confidence level

        Be concise. Max 200 words.
        """

        analysis = await self.llm.generate(prompt, temperature=0.3, max_tokens=500)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "window_size": len(self._buffer),
            "analysis": analysis,
            "raw_data_count": len(self._buffer),
        }

    async def _call_llm(self) -> Dict[str, Any]:
        return {"finish_reason": "stop", "content": ""}

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        return ToolCall(tool_name=tool_name, input_args=args)

    def stop(self):
        """Stop the real-time stream"""
        self._running = False
