"""
SKT-AI-LABS Browser Agent Example
Demonstrates autonomous web navigation and data extraction
"""

import asyncio
from skt_ai_labs import WebBrowserAgent


async def main():
    """Run browser agent example"""

    print("🌐 SKT-AI-LABS Web Browser Agent Demo")
    print("=" * 50)

    # Initialize browser agent
    agent = WebBrowserAgent(
        headless=False,  # Set True for production
        model="gemini-2.5-pro",
    )

    # Example tasks
    tasks = [
        "Go to https://news.ycombinator.com and extract top 5 story titles with URLs",
        "Navigate to https://github.com/trending and get top 10 repositories",
        "Search Amazon for 'wireless headphones' and extract top 3 products with prices",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n📋 Task {i}: {task}")
        print("🤖 Executing...")

        result = await agent.execute(task)

        print(f"\n✅ Result:")
        print(result.answer[:1500])
        print("\n" + "-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
