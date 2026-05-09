"""
SKT-AI-LABS API Server
FastAPI backend for agent operations
"""

import asyncio
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..agents.deep_research.agent import DeepResearchAgent
from ..agents.rag_assistant.agent import RAGAssistantAgent
from ..agents.web_browser.agent import WebBrowserAgent
from ..agents.realtime.agent import RealtimeAgent
from ..core.supervisor import MultiAgentTeam, SKTSupervisor


# Request/Response models
class ResearchRequest(BaseModel):
    query: str
    model: str = "gemini-2.5-pro"
    depth: str = "deep"
    max_iterations: int = 15


class ChatRequest(BaseModel):
    question: str
    mode: str = "standard"
    chat_history: List[Dict[str, str]] = []


class BrowserRequest(BaseModel):
    task: str
    headless: bool = True


class TeamRequest(BaseModel):
    query: str
    agents: List[str] = ["researcher", "rag", "browser"]


class AgentResponse(BaseModel):
    success: bool
    answer: str
    metadata: Dict[str, Any]
    duration_ms: float


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔥 SKT-AI-LABS API Server starting...")
    yield
    # Shutdown
    print("👋 Server shutting down...")


app = FastAPI(
    title="SKT-AI-LABS ADK API",
    description="Production API for SKT-AI-LABS Agent Development Kit",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "SKT-AI-LABS ADK API",
        "version": "1.0.0",
        "status": "operational",
        "agents": ["deep_research", "rag_assistant", "web_browser", "realtime", "multi_agent"],
    }


@app.post("/research", response_model=AgentResponse)
async def research(request: ResearchRequest):
    """Execute deep research"""
    import time
    start = time.time()

    agent = DeepResearchAgent(model=request.model)
    result = await agent.research(request.query)

    return AgentResponse(
        success=True,
        answer=result.answer,
        metadata={
            "iterations": result.iterations,
            "sources": result.metadata.get("sources", []),
            "search_queries": result.metadata.get("search_queries_executed", 0),
        },
        duration_ms=(time.time() - start) * 1000,
    )


@app.post("/chat", response_model=AgentResponse)
async def chat(request: ChatRequest):
    """Chat with RAG assistant"""
    import time
    start = time.time()

    rag = RAGAssistantAgent()
    result = await rag.chat(request.question, mode=request.mode, chat_history=request.chat_history)

    return AgentResponse(
        success=True,
        answer=result.answer,
        metadata={
            "confidence": result.metadata.get("confidence", 0),
            "sources": result.metadata.get("sources", []),
            "retrieved_docs": result.metadata.get("retrieved_docs", 0),
        },
        duration_ms=(time.time() - start) * 1000,
    )


@app.post("/browse", response_model=AgentResponse)
async def browse(request: BrowserRequest):
    """Execute web browsing task"""
    import time
    start = time.time()

    agent = WebBrowserAgent(headless=request.headless)
    result = await agent.execute(request.task)

    return AgentResponse(
        success=True,
        answer=result.answer,
        metadata={
            "final_url": result.metadata.get("final_url", ""),
            "actions_executed": result.metadata.get("actions_executed", 0),
        },
        duration_ms=(time.time() - start) * 1000,
    )


@app.post("/team", response_model=AgentResponse)
async def team_execute(request: TeamRequest):
    """Execute with multi-agent team"""
    import time
    start = time.time()

    agents = {}
    if "researcher" in request.agents:
        agents["researcher"] = DeepResearchAgent()
    if "rag" in request.agents:
        agents["rag"] = RAGAssistantAgent()
    if "browser" in request.agents:
        agents["browser"] = WebBrowserAgent()

    team = MultiAgentTeam(agents=agents, supervisor=SKTSupervisor(strategy="adaptive"))
    results = await team.execute(request.query)

    # Combine results
    combined = "\n\n".join([
        f"## {name.upper()}\n{r.answer[:500]}"
        for name, r in results.items()
    ])

    return AgentResponse(
        success=True,
        answer=combined,
        metadata={
            "agents_used": list(results.keys()),
            "total_iterations": sum(r.iterations for r in results.values()),
        },
        duration_ms=(time.time() - start) * 1000,
    )


@app.websocket("/ws/realtime")
async def realtime_websocket(websocket: WebSocket):
    """WebSocket for real-time agent"""
    await websocket.accept()

    agent = RealtimeAgent()

    try:
        while True:
            message = await websocket.receive_text()
            data = await agent._analyze_chunk({"message": message})

            if data:
                await websocket.send_json(data)

    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        agent.stop()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "skt-ai-labs-adk"}
