# 🔥 SKT-AI-LABS Agent Development Kit (ADK)

> **The most powerful open-source AI Agent framework. Period.**
> 
> Built for Open Source Community.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)


# SKT-OM | 13B Agentic RAG System

[![HF Space](https://img.shields.io/badge/🤗_HuggingFace-Space-ff9d00?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/spaces/lablab-ai-amd-developer-hackathon/SKT-OM)
[![Model](https://img.shields.io/badge/🧠_TIGER--OM-13B-ff6b6b?style=for-the-badge)](https://huggingface.co/Shrijanagain/TIGER-OM)
[![GitHub](https://img.shields.io/badge/🐙_GitHub-Repo-181717?style=for-the-badge&logo=github)](https://github.com/SHRIJANAGAIN/SKT-AMD-FILES)
[![Demo](https://img.shields.io/badge/🌐_Live-Demo-00d4ff?style=for-the-badge&logo=render)](https://skt-amd-om.onrender.com/)
[![GGUF](https://img.shields.io/badge/📦_GGUF-Q4__K__M-39ff14?style=for-the-badge)](https://huggingface.co/Shrijanagain/TIGER-GGUF)
[![Hackathon](https://img.shields.io/badge/🏆_AMD-Hackathon_2026-bc13fe?style=for-the-badge)](https://lablab.ai/ai-hackathons/amd-developer/amd-om/skt-om-13b-llm-langgraph-agentic-rag)
[![PDF](https://img.shields.io/badge/📊_Presentation-PDF-ff006e?style=for-the-badge)](https://storage.googleapis.com/lablab-static-eu/presentations/submissions/c1v2zj9hlt13p54nlxxov7aq/c1v2zj9hlt13p54nlxxov7aq-1778393640909_r0a4kpyvnxq2uln14ueozvyy.pdf)

---

## ⚡ What is SKT-OM?

**SKT-OM** is a **13B Agentic RAG System** built for the **AMD Developer Hackathon 2026**. It combines:

| Component | Tech |
|-----------|------|
| 🧠 LLM | TIGER-OM 13B (trained on AMD Cloud) |
| 🎯 Inference | vLLM FP16 on AMD MI300X |
| 🔧 Runtime | ROCm 7.0 |
| 🧩 Agents | LangGraph Multi-Agent Orchestration |
| 🔌 Plugins | 73+ Google ADK Style Plugins |
| 📚 RAG | SKT RAG Pipeline (Multi-hop + Rerank) |
| 🎛️ Control | Think Mode + Supervisor |

---

## 📊 Stats

```
73+ Plugins     | 12 Categories    | 6 Core Agents
97.3% Accuracy  | 2.3s Avg Response
```

---

## 🔗 Quick Links

| Resource | Link |
|----------|------|
| 🤗 HuggingFace Space | [Live Demo on HF](https://huggingface.co/spaces/lablab-ai-amd-developer-hackathon/SKT-OM) |
| 🧠 TIGER-OM Model | [13B LLM](https://huggingface.co/Shrijanagain/TIGER-OM) |
| 🐙 GitHub Repo | [Source Code](https://github.com/SHRIJANAGAIN/SKT-AMD-FILES) |
| 🌐 Live Demo | [Render App](https://skt-amd-om.onrender.com/) |
| 📦 GGUF Quantized | [Q4_K_M](https://huggingface.co/Shrijanagain/TIGER-GGUF) |
| 🏆 Hackathon Page | [AMD Dev 2026](https://lablab.ai/ai-hackathons/amd-developer/amd-om/skt-om-13b-llm-langgraph-agentic-rag) |
| 📊 Presentation PDF | [Full Deck](https://storage.googleapis.com/lablab-static-eu/presentations/submissions/c1v2zj9hlt13p54nlxxov7aq/c1v2zj9hlt13p54nlxxov7aq-1778393640909_r0a4kpyvnxq2uln14ueozvyy.pdf) |

---

## 🚀 How It Works

```
🎯 User Query → 🧠 Think Mode → 🔌 Plugin Router → 📚 SKT RAG
                                              ↓
                        🤖 LangGraph Agents → ✅ Verify → 📤 Response
```

### 7-Step Pipeline

1. **🎯 User Query Input** — Natural language query
2. **🧠 Think Mode** — Intent classification + complexity assessment
3. **🔌 Plugin Router** — Dynamic tool loading (73+ plugins)
4. **📚 SKT RAG Retrieval** — Multi-hop search + rerank + compression
5. **🤖 LangGraph Execution** — Parallel/sequential agent orchestration
6. **✅ Verification** — Consistency checks + self-correction
7. **📤 Final Synthesis** — TIGER-OM 13B generates structured response

---

## 🔌 73+ Plugin Ecosystem

| Category | Count | Plugins |
|----------|-------|---------|
| 🔍 Search | 8 | Google, DuckDuckGo, Bing, News, Maps, Scraper, Wikipedia, ArXiv |
| 💻 Code | 10 | Python, JS, Java, Go, Rust, PHP, Reviewer, Test, Packages, Docker |
| 📊 Data | 9 | Pandas, Matplotlib, Plotly, NumPy, SciPy, Sklearn, CSV, JSON, Excel |
| 📡 Communication | 7 | Email, Slack, Twitter, SMS, Discord, Voice, Telegram |
| 🗄️ Database | 8 | PostgreSQL, MongoDB, Redis, MySQL, ChromaDB, Pinecone, BigQuery, SQLite |
| ☁️ Cloud | 6 | AWS S3, Azure Blob, GCP Storage, Docker Hub, Kubernetes, Cloud Functions |
| 🤖 AI/ML | 7 | OpenAI GPT, HuggingFace, Claude, Image Gen, Speech, Summary, Translate |
| 🔒 Security | 5 | Auth, Rate Limit, PII, Vulnerability Scan, Encryption |
| 📈 Monitoring | 6 | Prometheus, Logs, APM, Alerts, Health, SLO |
| ⚙️ Automation | 5 | Workflow, Cron, Webhook, CI/CD, Task Queue |
| 🔗 Integration | 4 | GitHub, GitLab, Jira, Notion |

---

## 🛠️ Tech Stack

```yaml
GPU:        AMD MI300X
Framework:  ROCm 7.0
Inference:  vLLM FP16
LLM:        TIGER-OM 13B
Agents:     LangGraph
RAG:        SKT RAG (ChromaDB + BGE-large)
Plugins:    Google ADK Style Architecture
Frontend:   HTML/CSS/JS (Cyberpunk Theme)
```

---

## 📦 Installation

```bash
git clone https://github.com/SHRIJANAGAIN/SKT-AMD-FILES.git
cd SKT-AMD-FILES
pip install -r requirements.txt
python app.py
```

---



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
│  │  Gemini │ GPT-4 │ Llama │ Claude │SKT-OMNI-SUPREME      │           │
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

**Built with ❤️ by SKT-AI-LABS** | *Working For Open Source Community*
