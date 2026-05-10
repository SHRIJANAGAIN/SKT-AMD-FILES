"""
SKT-AI-LABS Deep Research Example
Demonstrates multi-step research with web search and synthesis
"""

import asyncio
from skt_ai_labs import DeepResearchAgent


async def main():
    """Run deep research example"""

    print("🔥 SKT-AI-LABS Deep Research Agent Demo")
    print("=" * 50)

    # Initialize agent
    agent = DeepResearchAgent(
        model="gemini-2.5-pro",  # or "gpt-4o", "llama-3.3-70b"
        search_provider="auto",   # Auto-fallback: Tavily -> Brave -> DuckDuckGo
    )

    # Research query
    query = "Latest breakthroughs in quantum error correction 2026"

    print(f"\n📋 Query: {query}")
    print("🔍 Starting deep research...\n")

    # Execute research
    result = await agent.research(query)

    # Display results
    print(f"✅ Research Complete!")
    print(f"   Iterations: {result.iterations}")
    print(f"   Duration: {result.total_duration_ms/1000:.1f}s")
    print(f"   Sources: {len(result.metadata.get('sources', []))}")
    print(f"   Search Queries: {result.metadata.get('search_queries_executed', 0)}")

    print("\n" + "=" * 50)
    print("📄 RESEARCH REPORT")
    print("=" * 50)
    print(result.answer[:2000])
    print("\n... [truncated for display]")

    # Save to file
    with open("research_report.md", "w") as f:
        f.write(f"# Research Report: {query}\n\n")
        f.write(result.answer)

    print("\n💾 Full report saved to research_report.md")


if __name__ == "__main__":
    asyncio.run(main())
