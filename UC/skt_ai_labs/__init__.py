"""
╔══════════════════════════════════════════════════════════════════════╗
║           🔥 SKT-AI-LABS Agent Development Kit (ADK) 🔥              ║
║                                                                      ║
║  A production-grade, real-time AI Agent framework with:             ║
║  • Deep Research Agent (Multi-step reasoning + Web search)          ║
║  • RAG Assistant (Vector DB + LangGraph workflows)                   ║
║  • Web Browser Agent (Automated browsing + Scraping)                ║
║  • Real-time Streaming (Live data processing)                       ║
║  • Multi-Agent Orchestration (Supervisor pattern)                    ║
║                                                                      ║
║  Built for Hackathons. Built for Production.                        ║
║  © 2026 SKT-AI-LABS. All rights reserved.                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

__version__ = "1.0.0"
__author__ = "SKT-AI-LABS"
__license__ = "MIT"

from .core.agent import SKTAgent, AgentConfig
from .core.supervisor import SKTSupervisor, MultiAgentTeam
from .agents.deep_research.agent import DeepResearchAgent
from .agents.rag_assistant.agent import RAGAssistantAgent
from .agents.web_browser.agent import WebBrowserAgent
from .agents.realtime.agent import RealtimeAgent
from .tools.search.web_search import SKTWebSearch
from .tools.browser.automation import SKTBrowser
from .tools.scraper.intelligent_scraper import IntelligentScraper
from .memory.vector_store import SKTVectorStore
from .llm.provider import SKTLLMProvider

__all__ = [
    "SKTAgent",
    "AgentConfig", 
    "SKTSupervisor",
    "MultiAgentTeam",
    "DeepResearchAgent",
    "RAGAssistantAgent",
    "WebBrowserAgent",
    "RealtimeAgent",
    "SKTWebSearch",
    "SKTBrowser",
    "IntelligentScraper",
    "SKTVectorStore",
    "SKTLLMProvider",
]
