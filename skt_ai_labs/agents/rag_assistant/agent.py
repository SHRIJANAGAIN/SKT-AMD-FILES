"""
SKT-AI-LABS RAG Assistant Agent
LangGraph-powered retrieval with multi-hop reasoning
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import structlog
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ...core.agent import SKTAgent, AgentConfig, AgentRunResult, ToolCall
from ...memory.vector_store import SKTVectorStore
from ...llm.provider import SKTLLMProvider
from ...tools.search.web_search import SKTWebSearch

logger = structlog.get_logger("skt_ai_labs.agents.rag")


class RAGState(dict):
    """LangGraph state for RAG"""
    question: str
    chat_history: List[Dict[str, str]]
    retrieved_docs: List[Document]
    web_results: List[Dict]
    reasoning_steps: List[str]
    answer: str
    confidence: float
    sources: List[str]
    needs_web_search: bool


class RAGAssistantAgent(SKTAgent):
    """
    SKT-AI-LABS RAG Assistant Agent

    Features:
    - Vector similarity search (ChromaDB/pgvector/FAISS)
    - Multi-hop reasoning (follow-up questions to refine retrieval)
    - Web search fallback when knowledge base insufficient
    - Source attribution for every claim
    - Confidence scoring
    - Conversation memory
    - Streaming support

    Built on LangGraph for complex reasoning workflows.
    """

    def __init__(self,
                 config: Optional[AgentConfig] = None,
                 vector_store_type: str = "chroma",
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 collection_name: str = "skt_knowledge",
                 enable_web_fallback: bool = True):

        cfg = config or AgentConfig()
        cfg.name = "skt_rag_assistant"
        cfg.description = "SKT-AI-LABS RAG Assistant - Knowledge base Q&A with reasoning"
        cfg.max_iterations = 5  # Multi-hop iterations

        super().__init__(cfg)

        self.vector_store = SKTVectorStore(
            store_type=vector_store_type,
            embedding_model=embedding_model,
            collection_name=collection_name,
        )
        self.llm = SKTLLMProvider(model=cfg.model)
        self.enable_web_fallback = enable_web_fallback
        self.web_search = SKTWebSearch() if enable_web_fallback else None

        # Build LangGraph
        self._graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph for RAG with reasoning"""
        workflow = StateGraph(RAGState)

        workflow.add_node("retrieve", self._node_retrieve)
        workflow.add_node("evaluate", self._node_evaluate)
        workflow.add_node("web_search", self._node_web_search)
        workflow.add_node("reason", self._node_reason)
        workflow.add_node("generate", self._node_generate)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            self._check_sufficiency,
            {"web_search": "web_search", "reason": "reason"}
        )
        workflow.add_edge("web_search", "reason")
        workflow.add_conditional_edges(
            "reason",
            self._should_continue_reasoning,
            {"retrieve": "retrieve", "generate": "generate"}
        )
        workflow.add_edge("generate", END)

        return workflow.compile(checkpointer=MemorySaver())

    async def _node_retrieve(self, state: RAGState) -> RAGState:
        """Retrieve documents from vector store"""
        question = state["question"]

        # Generate multiple query variations for better retrieval
        queries = await self._generate_query_variations(question)

        all_docs = []
        for q in queries:
            docs = await self.vector_store.similarity_search(q, k=5)
            all_docs.extend(docs)

        # Deduplicate and rank
        seen = set()
        unique_docs = []
        for doc in all_docs:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                unique_docs.append(doc)

        state["retrieved_docs"] = unique_docs[:10]  # Top 10
        state["reasoning_steps"] = state.get("reasoning_steps", []) + [f"Retrieved {len(unique_docs)} documents"]

        self._logger.info("retrieval_complete", docs=len(unique_docs), queries=len(queries))
        return state

    async def _node_evaluate(self, state: RAGState) -> RAGState:
        """Evaluate if retrieved docs are sufficient"""
        docs = state["retrieved_docs"]
        question = state["question"]

        if not docs:
            state["needs_web_search"] = True
            return state

        # Use LLM to judge sufficiency
        eval_prompt = f"""
        Question: {question}

        Retrieved documents:
        {self._format_docs(docs[:3])}

        Can these documents fully answer the question? 
        Answer ONLY "sufficient" or "insufficient".
        """

        response = await self.llm.generate(eval_prompt, temperature=0.1)

        state["needs_web_search"] = "insufficient" in response.lower()
        state["reasoning_steps"] = state.get("reasoning_steps", []) + [
            f"Knowledge base {'insufficient' if state['needs_web_search'] else 'sufficient'}"
        ]

        return state

    async def _node_web_search(self, state: RAGState) -> RAGState:
        """Fallback to web search"""
        if not self.web_search:
            return state

        question = state["question"]

        async with self.web_search:
            results = await self.web_search.search(question, num_results=5, search_depth="basic")

        web_docs = []
        for r in results:
            web_docs.append(Document(
                page_content=f"{r.title}\n{r.snippet}",
                metadata={"source": r.url, "type": "web"}
            ))

        state["web_results"] = [{"title": r.title, "url": r.url} for r in results]
        state["retrieved_docs"] = state.get("retrieved_docs", []) + web_docs
        state["reasoning_steps"] = state.get("reasoning_steps", []) + [f"Web search: {len(results)} results"]

        self._logger.info("web_search_complete", results=len(results))
        return state

    async def _node_reason(self, state: RAGState) -> RAGState:
        """Multi-hop reasoning: analyze and generate follow-up if needed"""
        docs = state["retrieved_docs"]
        question = state["question"]
        steps = state.get("reasoning_steps", [])

        if len(steps) >= self.config.max_iterations:
            return state

        # Analyze gaps
        reason_prompt = f"""
        Question: {question}

        Current reasoning steps:
        {chr(10).join(steps)}

        Available information:
        {self._format_docs(docs[:3])}

        What additional information is needed? Return:
        - "sufficient" if enough info
        - A follow-up question to retrieve missing info
        """

        response = await self.llm.generate(reason_prompt, temperature=0.3)

        if "sufficient" not in response.lower() and "?" in response:
            # Need another retrieval hop
            state["question"] = response.strip()
            state["reasoning_steps"] = steps + [f"Follow-up: {response.strip()}"]
        else:
            state["reasoning_steps"] = steps + ["Information sufficient"]

        return state

    async def _node_generate(self, state: RAGState) -> RAGState:
        """Generate final answer with citations"""
        docs = state["retrieved_docs"]
        question = state["question"]
        history = state.get("chat_history", [])

        # Build context with sources
        context = self._format_docs_with_sources(docs)

        prompt = f"""
        You are SKT-AI-LABS Knowledge Assistant. Answer based ONLY on the provided context.

        Chat History:
        {self._format_history(history)}

        Context:
        {context}

        Question: {question}

        Rules:
        1. Every claim MUST cite its source [Source: X]
        2. If unsure, say "I don't have enough information"
        3. Be concise but thorough
        4. Include confidence level: High/Medium/Low
        """

        answer = await self.llm.generate(prompt, temperature=0.3, max_tokens=2000)

        # Extract confidence
        confidence = 0.8 if "High" in answer else (0.5 if "Medium" in answer else 0.3)

        # Extract sources
        sources = list(set(re.findall(r'Source: (\S+)', answer)))

        state["answer"] = answer
        state["confidence"] = confidence
        state["sources"] = sources

        return state

    def _check_sufficiency(self, state: RAGState) -> str:
        """Route to web search or reasoning"""
        return "web_search" if state.get("needs_web_search") else "reason"

    def _should_continue_reasoning(self, state: RAGState) -> str:
        """Check if more reasoning hops needed"""
        steps = state.get("reasoning_steps", [])
        if len(steps) >= self.config.max_iterations:
            return "generate"
        if any("Follow-up" in s for s in steps[-2:]):
            return "retrieve"  # Need more docs
        return "generate"

    async def _generate_query_variations(self, question: str) -> List[str]:
        """Generate query variations for better retrieval"""
        prompt = f"""
        Generate 3 search query variations for: {question}
        Return as JSON list: ["query1", "query2", "query3"]
        """

        response = await self.llm.generate(prompt, temperature=0.5)

        try:
            import json
            queries = json.loads(response)
            if isinstance(queries, list):
                return queries[:3]
        except:
            pass

        return [question]

    def _format_docs(self, docs: List[Document]) -> str:
        """Format documents for prompt"""
        return "\n\n".join([
            f"Document {i+1}:\n{d.page_content[:500]}"
            for i, d in enumerate(docs)
        ])

    def _format_docs_with_sources(self, docs: List[Document]) -> str:
        """Format with source attribution"""
        formatted = []
        for i, d in enumerate(docs):
            source = d.metadata.get("source", f"doc_{i+1}")
            formatted.append(f"[{source}]\n{d.page_content[:600]}")
        return "\n\n---\n\n".join(formatted)

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format chat history"""
        if not history:
            return "None"
        return "\n".join([
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content'][:100]}"
            for h in history[-5:]  # Last 5 exchanges
        ])

    async def ingest(self, sources: List[str], chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Ingest documents into knowledge base.

        Args:
            sources: List of file paths, URLs, or text strings
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        all_docs = []
        for source in sources:
            if source.startswith("http"):
                # URL - fetch and ingest
                docs = await self._fetch_url(source)
            elif os.path.isfile(source):
                # File
                docs = await self._read_file(source)
            else:
                # Raw text
                docs = [Document(page_content=source, metadata={"source": "text_input"})]

            chunks = splitter.split_documents(docs)
            all_docs.extend(chunks)

        await self.vector_store.add_documents(all_docs)
        self._logger.info("ingestion_complete", documents=len(sources), chunks=len(all_docs))

    async def _fetch_url(self, url: str) -> List[Document]:
        """Fetch URL content"""
        from ...tools.browser.automation import SKTBrowser

        async with SKTBrowser(headless=True) as browser:
            data = await browser.extract_content(url)
            return [Document(
                page_content=data.content,
                metadata={"source": url, "title": data.title}
            )]

    async def _read_file(self, path: str) -> List[Document]:
        """Read file content"""
        from langchain_community.document_loaders import TextLoader, PyPDFLoader

        if path.endswith(".pdf"):
            loader = PyPDFLoader(path)
        else:
            loader = TextLoader(path)

        return loader.load()

    async def chat(self, question: str, mode: str = "standard", chat_history: Optional[List[Dict]] = None) -> AgentRunResult:
        """
        Chat with the RAG assistant.

        Args:
            question: User question
            mode: "standard" or "deep" (multi-hop)
            chat_history: Previous conversation
        """
        initial_state = RAGState(
            question=question,
            chat_history=chat_history or [],
            retrieved_docs=[],
            web_results=[],
            reasoning_steps=[],
            answer="",
            confidence=0.0,
            sources=[],
            needs_web_search=False,
        )

        # Run graph
        final_state = await self._graph.ainvoke(initial_state)

        return AgentRunResult(
            run_id=self.run_id or "rag_run",
            agent_name=self.name,
            query=question,
            answer=final_state.get("answer", ""),
            tool_calls=[],
            iterations=len(final_state.get("reasoning_steps", [])),
            total_duration_ms=0,
            token_usage={},
            termination_reason="completed",
            metadata={
                "confidence": final_state.get("confidence", 0),
                "sources": final_state.get("sources", []),
                "retrieved_docs": len(final_state.get("retrieved_docs", [])),
                "web_results": len(final_state.get("web_results", [])),
            }
        )

    async def _call_llm(self) -> Dict[str, Any]:
        """Required by base class"""
        return {"finish_reason": "stop", "content": ""}

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        """Required by base class"""
        return ToolCall(tool_name=tool_name, input_args=args)
