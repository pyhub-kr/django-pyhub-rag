"""Agent CLI command."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ..agents import Tool, create_react_agent
from ..agents.tools import Calculator
from ..base import LLM

app = typer.Typer(
    help="Agent를 실행합니다.",
    pretty_exceptions_enable=False,
)
console = Console()


@app.command()
def run(
    question: str = typer.Argument(..., help="질문"),
    model: str = typer.Option("gpt-4o-mini", help="사용할 모델"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 로그 출력"),
    max_iterations: int = typer.Option(10, help="최대 반복 횟수"),
):
    """React Agent를 실행합니다."""
    
    # LLM 생성
    llm = LLM.create(model=model)
    
    # 도구 생성
    tools = [
        Tool(
            name="calculator",
            description="Performs mathematical calculations. Use this when you need to compute numbers.",
            func=Calculator().run,
            args_schema=Calculator().args_schema
        )
    ]
    
    # Agent 생성
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        verbose=verbose,
        max_iterations=max_iterations
    )
    
    # 실행
    console.print(Panel(f"[bold blue]Question:[/bold blue] {question}", expand=False))
    
    try:
        # 비동기 도구가 있는지 확인
        if hasattr(agent, 'arun'):
            # 비동기 실행
            result = asyncio.run(agent.arun(question))
        else:
            # 동기 실행
            result = agent.run(question)
        
        console.print("\n[bold green]Final Answer:[/bold green]")
        console.print(Panel(result, expand=False))
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def list_tools():
    """사용 가능한 도구 목록을 표시합니다."""
    
    tools = [
        {
            "name": "calculator",
            "description": "Performs mathematical calculations",
            "args": {
                "expression": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')"
            }
        }
    ]
    
    console.print("[bold]Available Tools:[/bold]\n")
    
    for tool in tools:
        console.print(f"[bold blue]{tool['name']}[/bold blue]")
        console.print(f"  Description: {tool['description']}")
        console.print("  Arguments:")
        for arg, desc in tool['args'].items():
            console.print(f"    - {arg}: {desc}")
        console.print()


if __name__ == "__main__":
    app()