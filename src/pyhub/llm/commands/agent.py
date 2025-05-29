"""Agent CLI command."""

import asyncio
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel

from pyhub import init
from ..agents import create_react_agent
from ..agents.tools import tool_registry
from .. import LLM

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
    tools: Optional[List[str]] = typer.Option(None, "--tool", "-t", help="사용할 도구 (여러 개 지정 가능)"),
):
    """React Agent를 실행합니다."""
    
    # Django 초기화
    init()
    
    # LLM 생성
    llm = LLM.create(model=model)
    
    # 도구 생성 - 레지스트리에서 도구 가져오기
    agent_tools = []
    
    if tools:
        # 지정된 도구만 사용
        for tool_name in tools:
            tool = tool_registry.create_tool(tool_name)
            if tool:
                agent_tools.append(tool)
            else:
                console.print(f"[yellow]Warning: Tool '{tool_name}' not found[/yellow]")
    else:
        # 모든 도구 사용
        for tool_info in tool_registry.list_tools():
            tool = tool_registry.create_tool(tool_info['name'])
            if tool:
                agent_tools.append(tool)
    
    if not agent_tools:
        console.print("[red]Error: No tools available[/red]")
        raise typer.Exit(1)
    
    # Agent 생성
    agent = create_react_agent(
        llm=llm,
        tools=agent_tools,
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
        import traceback
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        if verbose:
            console.print("\n[bold red]Traceback:[/bold red]")
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def list_tools():
    """사용 가능한 도구 목록을 표시합니다."""
    
    # Django 초기화
    init()
    
    tools = tool_registry.list_tools()
    
    console.print("[bold]Available Tools:[/bold]\n")
    
    for tool in tools:
        console.print(f"[bold blue]{tool['name']}[/bold blue]")
        console.print(f"  Description: {tool['description']}")
        if tool['args']:
            console.print("  Arguments:")
            for arg, desc in tool['args'].items():
                console.print(f"    - {arg}: {desc}")
        else:
            console.print("  Arguments: None")
        console.print()


if __name__ == "__main__":
    app()