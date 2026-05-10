"""
SKT-AI-LABS RAG Chatbot Example
Demonstrates knowledge base Q&A with multi-hop reasoning
"""

import asyncio
from skt_ai_labs import RAGAssistantAgent


async def main():
    """Run RAG chatbot example"""

    print("💬 SKT-AI-LABS RAG Assistant Demo")
    print("=" * 50)

    # Initialize RAG agent
    rag = RAGAssistantAgent(
        vector_store_type="chroma",  # or "pgvector", "faiss"
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        collection_name="demo_knowledge",
        enable_web_fallback=True,  # Fall back to web search if KB insufficient
    )

    # Ingest documents (PDFs, text files, URLs)
    print("\n📥 Ingesting knowledge base...")
    await rag.ingest([
        "https://arxiv.org/abs/2401.00001",  # Example URL
        "./docs/company_handbook.pdf",        # Example file
        "SKT-AI-LABS is a leading AI research company founded in 2026.",  # Raw text
    ])

    print("✅ Knowledge base ready!\n")

    # Chat loop
    chat_history = []

    while True:
        question = input("\n🧑 You: ")

        if question.lower() in ["exit", "quit", "bye"]:
            print("👋 Goodbye!")
            break

        print("🤖 Thinking...")

        result = await rag.chat(
            question=question,
            mode="deep",  # "standard" or "deep" (multi-hop)
            chat_history=chat_history,
        )

        print(f"\n🤖 SKT-AI-LABS: {result.answer}")
        print(f"\n[Confidence: {result.metadata.get('confidence', 0):.0%} | "
              f"Sources: {len(result.metadata.get('sources', []))} | "
              f"Docs: {result.metadata.get('retrieved_docs', 0)}]")

        # Update history
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": result.answer})


if __name__ == "__main__":
    asyncio.run(main())
