# SKT-AI-LABS ADK Architecture

## Overview

SKT-AI-LABS Agent Development Kit (ADK) is a production-grade framework for building, deploying, and orchestrating AI agents.

## Core Components

### 1. Agent Layer

```
┌─────────────────────────────────────────┐
│           Agent Layer                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  Deep   │ │   RAG   │ │  Web    │  │
│  │Research │ │Assistant│ │ Browser │  │
│  └────┬────┘ └────┬────┘ └────┬────┘  │
│       └───────────┼───────────┘        │
│                   │                    │
│            ┌──────┴──────┐             │
│            │   Base      │             │
│            │   Agent     │             │
│            └─────────────┘             │
└─────────────────────────────────────────┘
```

All agents inherit from `SKTAgent` base class which provides:
- State management (IDLE → RUNNING → COMPLETED/FAILED)
- Guardrails (timeout, iteration limits, token budgets)
- Error taxonomy (Retryable/NonRetryable/Degraded)
- Audit trails
- Loop detection
- Concurrent execution

### 2. Tool Layer

```
┌─────────────────────────────────────────┐
│           Tool Layer                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Search  │ │ Browser │ │ Scraper │   │
│  │ Engine  │ │  Auto   │ │ Intel.  │   │
│  │(Multi)  │ │         │ │         │   │
│  └─────────┘ └─────────┘ └─────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Vector  │ │  LLM    │ │  Cache  │   │
│  │ Store   │ │Provider │ │         │   │
│  └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────┘
```

### 3. Orchestration Layer

The `SKTSupervisor` manages multi-agent teams:
- **Sequential**: One after another
- **Parallel**: All simultaneously
- **Adaptive**: LLM decides routing
- **Hierarchical**: Tree structure

### 4. Memory Layer

Vector storage backends:
- **ChromaDB**: Local, persistent
- **pgvector**: Production PostgreSQL
- **FAISS**: Fast, in-memory
- **Redis**: Caching + vectors

## Data Flow

```
User Query → Supervisor → Agent Selection → Tool Execution → Synthesis → Response
                ↓
         [Deep Research] → Search → Scrape → Analyze → Report
         [RAG Assistant] → Retrieve → Reason → Generate
         [Web Browser]   → Navigate → Interact → Extract
         [Real-time]     → Stream → Window Analysis → Alert
```

## Error Handling

Three-tier error taxonomy:

| Category | Action | Examples |
|----------|--------|----------|
| **Retryable** | Exponential backoff | Timeout, 429, 503 |
| **NonRetryable** | Fail immediately | Bad auth, malformed input |
| **Degraded** | Continue with partial | 403 paywall, 404 |

## Security

- No API keys in source code
- Environment variable configuration
- HttpOnly cookies for auth
- Rate limiting on all endpoints
- SQL injection protection (SQLModel)
- CORS whitelist

## Performance

- Async/await throughout
- Concurrent tool execution via `asyncio.gather`
- Connection pooling
- Intelligent history pruning
- Token budget management
- Lazy initialization
