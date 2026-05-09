# 🔥 SKT-AI-LABS Agent Development Kit (ADK)

> **The most powerful open-source AI Agent framework. Period.**
> 
> Built for hackathon winners. Built for production warriors.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)

## 🚀 What Makes SKT-AI-LABS ADK Different?

Unlike generic wrappers around OpenAI or Google APIs, **SKT-AI-LABS ADK** is a **complete agent operating system**:

| Feature | Others | SKT-AI-LABS ADK |
|---------|--------|-----------------|
| **Deep Research** | Single search call | Multi-step reasoning + recursive exploration |
| **RAG** | Basic retrieval | LangGraph-powered multi-hop reasoning |
| **Web Browser** | Static scraping | Live Playwright automation with anti-bot evasion |
| **Real-time** | Polling | WebSocket streaming + live data ingestion |
| **Error Handling** | Crash on failure | 3-tier taxonomy: Retryable/NonRetryable/Degraded |
| **Observability** | Print statements | Structured logging with full audit trails |
| **Multi-Agent** | Manual orchestration | Supervisor pattern with automatic routing |

## 📦 Installation

```bash
# Standard install
pip install skt-ai-labs-adk

# With browser automation support
pip install skt-ai-labs-adk[browser]

# Development install
pip install skt-ai-labs-adk[dev]
```

## 🎯 Quick Start

### 1. Deep Research Agent
```python
from skt_ai_labs import DeepResearchAgent

agent = DeepResearchAgent(
    model="gemini-2.5-pro",  # or "gpt-4o", "llama-3.3-70b"
    max_iterations=15,
    search_depth="deep"
)

report = await agent.research(
    "Latest quantum computing breakthroughs 2026"
)
print(report.markdown)
```

### 2. RAG Assistant with LangGraph
```python
from skt_ai_labs import RAGAssistantAgent

rag = RAGAssistantAgent(
    vector_store="chroma",  # or "pgvector", "faiss"
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)

# Ingest documents
await rag.ingest(["docs/*.pdf", "docs/*.txt"])

# Chat with reasoning
response = await rag.chat(
    "What are the key findings about neural architecture search?",
    mode="deep"  # multi-hop reasoning
)
```

### 3. Web Browser Agent
```python
from skt_ai_labs import WebBrowserAgent

browser = WebBrowserAgent(headless=True)

# Navigate, interact, scrape
result = await browser.execute("""
1. Go to https://news.ycombinator.com
2. Find the top 5 stories about AI
3. Extract title, URL, and comment count
4. Return as structured JSON
""")
```

### 4. Real-time Streaming Agent
```python
from skt_ai_labs import RealtimeAgent

rt = RealtimeAgent(stream_type="websocket")

async for chunk in rt.process_stream("live_stock_data"):
    print(chunk.analysis)
```

### 5. Multi-Agent Team (Supervisor)
```python
from skt_ai_labs import SKTSupervisor, MultiAgentTeam

team = MultiAgentTeam(
    agents={
        "researcher": DeepResearchAgent(),
        "browser": WebBrowserAgent(),
        "rag": RAGAssistantAgent(),
    },
    supervisor=SKTSupervisor(strategy="adaptive")
)

result = await team.execute(
    "Research the latest AI trends, browse specific sites, and answer from our knowledge base"
)
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SKT-AI-LABS ADK                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Deep       │  │    RAG       │  │   Web        │          │
│  │   Research   │  │   Assistant  │  │  Browser     │          │
│  │   Agent      │  │   Agent      │  │   Agent      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                    ┌──────┴──────┐                              │
│                    │  SKT        │                              │
│                    │ Supervisor  │                              │
│                    │  (Router)   │                              │
│                    └──────┬──────┘                              │
│                           │                                     │
│  ┌────────────────────────┼────────────────────────┐           │
│  │           TOOL LAYER   │                        │           │
│  │  ┌────────┐ ┌────────┐ │ ┌────────┐ ┌────────┐ │           │
│  │  │Search  │ │Browser │ │ │Scraper │ │Vector  │ │           │
│  │  │Engine  │ │Auto    │ │ │Intel.  │ │Store   │ │           │
│  │  └────────┘ └────────┘ │ └────────┘ └────────┘ │           │
│  └────────────────────────┼────────────────────────┘           │
│                           │                                     │
│  ┌────────────────────────┼────────────────────────┐           │
│  │         LLM LAYER      │                        │           │
│  │  Gemini │ GPT-4 │ Llama │ Claude │ Custom      │           │
│  └────────────────────────┴────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration

Create `.env` file:
```env
# LLM APIs (at least one required)
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key

# Search APIs
TAVILY_API_KEY=your_tavily_key
BRAVE_API_KEY=your_brave_key
SERPAPI_KEY=your_serpapi_key

# Database (for RAG)
DATABASE_URL=postgresql://user:pass@localhost:5432/skt_db

# Vector Store
VECTOR_STORE_TYPE=chroma  # chroma, pgvector, faiss, redis
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Browser
PLAYWRIGHT_HEADLESS=true
BROWSER_TIMEOUT=30000
ANTI_BOT_ENABLED=true

# Agent Settings
MAX_ITERATIONS=15
MAX_CONCURRENT_SEARCHES=10
TOKEN_BUDGET=128000
LOG_LEVEL=INFO
```

## 📚 Documentation

- [Architecture Guide](docs/architecture.md)
- [Agent Development](docs/agents.md)
- [Tool Creation](docs/tools.md)
- [Deployment Guide](docs/deployment.md)
- [API Reference](docs/api.md)

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

**Built with ❤️ by SKT-AI-LABS**
