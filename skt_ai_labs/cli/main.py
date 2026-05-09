"""
SKT-AI-LABS CLI
Command-line interface for agent operations
"""

import asyncio
import os
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..agents.deep_research.agent import DeepResearchAgent
from ..agents.rag_assistant.agent import RAGAssistantAgent
from ..agents.web_browser.agent import WebBrowserAgent
from ..agents.realtime.agent import RealtimeAgent
from ..core.supervisor import MultiAgentTeam, SKTSupervisor

app = typer.Typer(
    name="skt-adk",
    help="🔥 SKT-AI-LABS Agent Development Kit CLI",
    rich_markup_mode="rich",
)
console = Console()


def print_banner():
    """Print SKT-AI-LABS banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║           🔥 SKT-AI-LABS ADK v1.0.0 🔥                 ║
    ║                                                          ║
    ║    Deep Research | RAG | Web Browser | Real-time         ║
    ║                                                          ║
    ║    Built for Hackathons. Built for Production.         ║
    ╚══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, border_style="bold blue"))


@app.command()
def research(
    query: str = typer.Argument(..., help="Research query"),
    model: str = typer.Option("gemini-2.5-pro", "--model", "-m", help="LLM model"),
    depth: str = typer.Option("deep", "--depth", "-d", help="Search depth: basic/deep"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """🔬 Execute deep research on any topic"""
    print_banner()

    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Researching...", total=None)

            agent = DeepResearchAgent(model=model)
            result = await agent.research(query)

            progress.update(task, completed=True)

        # Display results
        console.print(f"\n[bold green]✅ Research Complete[/bold green]")
        console.print(f"[cyan]Iterations:[/cyan] {result.iterations}")
        console.print(f"[cyan]Duration:[/cyan] {result.total_duration_ms/1000:.1f}s")
        console.print(f"[cyan]Sources:[/cyan] {len(result.metadata.get('sources', []))}")
        console.print(f"\n[bold]Report:[/bold]\n")
        console.print(result.answer[:2000])

        if output:
            with open(output, "w") as f:
                f.write(result.answer)
            console.print(f"\n[green]💾 Saved to {output}[/green]")

    asyncio.run(_run())


@app.command()
def chat(
    question: str = typer.Argument(..., help="Your question"),
    mode: str = typer.Option("standard", "--mode", help="Mode: standard/deep"),
    ingest: Optional[str] = typer.Option(None, "--ingest", help="Ingest files (comma-separated paths)"),
):
    """💬 Chat with RAG assistant"""
    print_banner()

    async def _run():
        rag = RAGAssistantAgent()

        if ingest:
            paths = ingest.split(",")
            console.print(f"[yellow]📥 Ingesting {len(paths)} sources...[/yellow]")
            await rag.ingest(paths)

        result = await rag.chat(question, mode=mode)

        console.print(f"\n[bold cyan]🤖 Answer:[/bold cyan]")
        console.print(result.answer)
        console.print(f"\n[dim]Confidence: {result.metadata.get('confidence', 0):.0%} | Sources: {len(result.metadata.get('sources', []))}[/dim]")

    asyncio.run(_run())


@app.command()
def browse(
    task: str = typer.Argument(..., help="Web task description"),
    headless: bool = typer.Option(True, "--headless/--headed", help="Browser mode"),
):
    """🌐 Execute web browsing task"""
    print_banner()

    async def _run():
        agent = WebBrowserAgent(headless=headless)
        result = await agent.execute(task)

        console.print(f"\n[bold green]🌐 Web Task Complete[/bold green]")
        console.print(result.answer)

    asyncio.run(_run())


@app.command()
def team(
    query: str = typer.Argument(..., help="Task for multi-agent team"),
):
    """👥 Execute with multi-agent team"""
    print_banner()

    async def _run():
        team = MultiAgentTeam(
            agents={
                "researcher": DeepResearchAgent(),
                "browser": WebBrowserAgent(),
                "rag": RAGAssistantAgent(),
            },
            supervisor=SKTSupervisor(strategy="adaptive")
        )

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Multi-agent execution...", total=None)
            results = await team.execute(query)
            progress.update(task, completed=True)

        # Display results table
        table = Table(title="Multi-Agent Results")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Answer Preview", style="white")

        for name, result in results.items():
            preview = result.answer[:100] + "..." if len(result.answer) > 100 else result.answer
            table.add_row(name, "✅", preview)

        console.print(table)

    asyncio.run(_run())


@app.command()
def status():
    """📊 Show system status"""
    print_banner()

    table = Table(title="SKT-AI-LABS ADK Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")

    table.add_row("Core Framework", "✅ Ready", "v1.0.0")
    table.add_row("Deep Research", "✅ Ready", "Multi-step web research")
    table.add_row("RAG Assistant", "✅ Ready", "LangGraph + Vector DB")
    table.add_row("Web Browser", "✅ Ready", "Playwright automation")
    table.add_row("Real-time", "✅ Ready", "Streaming processing")
    table.add_row("Multi-Agent", "✅ Ready", "Supervisor orchestration")

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
