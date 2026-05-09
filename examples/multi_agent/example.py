"""
SKT-AI-LABS Multi-Agent Team Example
Demonstrates supervisor-orchestrated multi-agent execution
"""

import asyncio
from skt_ai_labs import (
    DeepResearchAgent, 
    RAGAssistantAgent, 
    WebBrowserAgent,
    MultiAgentTeam,
    SKTSupervisor,
)


async def main():
    """Run multi-agent team example"""

    print("👥 SKT-AI-LABS Multi-Agent Team Demo")
    print("=" * 50)

    # Create individual agents
    researcher = DeepResearchAgent(model="gemini-2.5-pro")
    browser = WebBrowserAgent(headless=True)
    rag = RAGAssistantAgent(vector_store_type="chroma")

    # Create team with adaptive supervisor
    team = MultiAgentTeam(
        agents={
            "deep_researcher": researcher,
            "web_browser": browser,
            "knowledge_base": rag,
        },
        supervisor=SKTSupervisor(strategy="adaptive")
    )

    # Complex query requiring multiple capabilities
    query = """
    Research the latest developments in autonomous AI agents in 2026.
    Browse specific company websites (Anthropic, OpenAI, Google) for their latest announcements.
    Also check our internal knowledge base for any previous research on this topic.
    Compile a comprehensive report with citations.
    """

    print(f"\n📋 Complex Query:")
    print(query[:200] + "...")
    print("\n🤖 Multi-Agent Execution Starting...")
    print("   [Supervisor analyzing query and routing to best agents...]")

    # Execute
    results = await team.execute(query)

    # Display results
    print("\n" + "=" * 50)
    print("📊 MULTI-AGENT RESULTS")
    print("=" * 50)

    for agent_name, result in results.items():
        print(f"\n🔹 {agent_name.upper()}")
        print(f"   Status: {result.termination_reason}")
        print(f"   Iterations: {result.iterations}")
        print(f"   Duration: {result.total_duration_ms/1000:.1f}s")
        print(f"   Answer Preview:")
        print(f"   {result.answer[:300]}...")

    # Combined synthesis
    print("\n" + "=" * 50)
    print("📝 SYNTHESIZED REPORT")
    print("=" * 50)

    combined = "\n\n".join([
        f"## {name.replace('_', ' ').title()}\n{r.answer[:500]}"
        for name, r in results.items()
    ])
    print(combined)

    # Save
    with open("multi_agent_report.md", "w") as f:
        f.write("# Multi-Agent Research Report\n\n")
        f.write(combined)

    print("\n💾 Report saved to multi_agent_report.md")


if __name__ == "__main__":
    asyncio.run(main())
