import logging
from pathlib import Path
from typing import Optional

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pyhub import init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum

console = Console()


def compare(
    ctx: typer.Context,
    query: Optional[str] = typer.Argument(None, help="비교할 질문"),
    models: list[LLMChatModelEnum] = typer.Option(
        [LLMChatModelEnum.GPT_4O_MINI, LLMChatModelEnum.CLAUDE_HAIKU_3_5_LATEST],
        "--model",
        "-m",
        help="비교할 모델들 (여러 개 지정 가능)",
    ),
    system_prompt: str = typer.Option(
        None,
        "--system-prompt",
        "-s",
        help="시스템 프롬프트",
    ),
    temperature: float = typer.Option(
        0.7,
        "--temperature",
        "-t",
        help="응답 온도",
    ),
    max_tokens: int = typer.Option(
        1000,
        "--max-tokens",
        help="최대 토큰 수",
    ),
    output_format: str = typer.Option(
        "side-by-side",
        "--format",
        "-f",
        help="출력 형식 (side-by-side, sequential, table)",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="결과 저장 경로 (JSON)",
    ),
    show_cost: bool = typer.Option(
        True,
        "--cost/--no-cost",
        help="비용 비교 표시",
    ),
    show_time: bool = typer.Option(
        True,
        "--time/--no-time",
        help="응답 시간 비교 표시",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """여러 LLM 모델의 응답을 비교합니다."""

    # query가 없으면 help 출력
    if not query:
        console.print(ctx.get_help())
        raise typer.Exit()

    if len(models) < 2:
        console.print("[red]오류: 최소 2개 이상의 모델을 지정해야 합니다.[/red]")
        console.print('[dim]예: pyhub.llm compare "질문" -m gpt-4o-mini -m claude-3-5-haiku-latest[/dim]')
        raise typer.Exit(1)

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    # 비교 시작
    console.print("\n[bold blue]🔍 모델 비교[/bold blue]")
    console.print(f"[dim]질문: {query}[/dim]")
    console.print(f"[dim]모델: {', '.join([m.value for m in models])}[/dim]\n")

    results = []

    # 각 모델로 질의
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def query_model(model_enum):
        """단일 모델에 질의"""
        try:
            llm = LLM.create(
                model=model_enum,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            start_time = time.time()
            response_text = ""
            usage = None

            # 스트리밍 대신 일반 응답으로 받기 (비교를 위해)
            response = llm.ask(query, stream=False, enable_cache=enable_cache)
            response_text = response.text
            usage = response.usage if hasattr(response, "usage") else None

            elapsed_time = time.time() - start_time

            # 비용 계산
            cost_info = None
            if show_cost and usage:
                try:
                    from pyhub.llm.utils.pricing import calculate_cost

                    cost_info = calculate_cost(model_enum.value, usage.input, usage.output)
                except:
                    pass

            return {
                "model": model_enum.value,
                "response": response_text,
                "time": elapsed_time,
                "usage": (
                    {
                        "input": usage.input if usage else 0,
                        "output": usage.output if usage else 0,
                        "total": usage.total if usage else 0,
                    }
                    if usage
                    else None
                ),
                "cost": cost_info,
                "success": True,
                "error": None,
            }
        except Exception as e:
            return {
                "model": model_enum.value,
                "response": None,
                "time": 0,
                "usage": None,
                "cost": None,
                "success": False,
                "error": str(e),
            }

    # 병렬 처리
    with console.status("[bold green]모델들에게 질의 중...") as status:
        with ThreadPoolExecutor(max_workers=len(models)) as executor:
            future_to_model = {executor.submit(query_model, model): model for model in models}

            for future in as_completed(future_to_model):
                result = future.result()
                results.append(result)
                if result["success"]:
                    status.update(f"[bold green]✓ {result['model']} 완료[/bold green]")
                else:
                    status.update(f"[bold red]✗ {result['model']} 실패[/bold red]")

    # 모델 순서대로 정렬
    results = sorted(results, key=lambda x: [m.value for m in models].index(x["model"]))

    # 결과 출력
    if output_format == "side-by-side":
        # 나란히 표시
        panels = []
        for result in results:
            if result["success"]:
                content = result["response"]
                if show_time:
                    content += f"\n\n[dim]응답 시간: {result['time']:.2f}초[/dim]"
                if show_cost and result["cost"]:
                    content += f"\n[dim]비용: ${result['cost']['total_cost']:.6f}[/dim]"
            else:
                content = f"[red]오류: {result['error']}[/red]"

            panels.append(Panel(content, title=result["model"], expand=True))

        console.print(Columns(panels, equal=True))

    elif output_format == "sequential":
        # 순차적 표시
        for result in results:
            console.print(f"\n[bold blue]━━━ {result['model']} ━━━[/bold blue]")
            if result["success"]:
                console.print(result["response"])
                if show_time:
                    console.print(f"\n[dim]응답 시간: {result['time']:.2f}초[/dim]")
                if show_cost and result["cost"]:
                    console.print(f"[dim]비용: ${result['cost']['total_cost']:.6f}[/dim]")
            else:
                console.print(f"[red]오류: {result['error']}[/red]")

    elif output_format == "table":
        # 테이블 형식
        table = Table(title="모델 비교 결과")
        table.add_column("모델", style="cyan")
        table.add_column("응답", style="green", overflow="fold")
        if show_time:
            table.add_column("시간(초)", style="yellow")
        if show_cost:
            table.add_column("비용($)", style="magenta")
        table.add_column("토큰", style="blue")

        for result in results:
            if result["success"]:
                response = result["response"][:100] + "..." if len(result["response"]) > 100 else result["response"]
                row = [result["model"], response]
                if show_time:
                    row.append(f"{result['time']:.2f}")
                if show_cost:
                    row.append(f"{result['cost']['total_cost']:.6f}" if result["cost"] else "N/A")
                row.append(f"{result['usage']['total']}" if result["usage"] else "N/A")
            else:
                row = [result["model"], f"[red]오류: {result['error']}[/red]"]
                if show_time:
                    row.append("N/A")
                if show_cost:
                    row.append("N/A")
                row.append("N/A")

            table.add_row(*row)

        console.print(table)

    # 통계 요약
    if show_time or show_cost:
        console.print("\n[bold]통계 요약[/bold]")

        if show_time:
            times = [r["time"] for r in results if r["success"]]
            if times:
                fastest = min(results, key=lambda x: x["time"] if x["success"] else float("inf"))
                console.print(f"가장 빠른 모델: [green]{fastest['model']}[/green] ({fastest['time']:.2f}초)")

        if show_cost:
            costs = [(r["model"], r["cost"]["total_cost"]) for r in results if r["success"] and r["cost"]]
            if costs:
                cheapest = min(costs, key=lambda x: x[1])
                console.print(f"가장 저렴한 모델: [green]{cheapest[0]}[/green] (${cheapest[1]:.6f})")

    # 결과 저장
    if output_path:
        try:
            import json

            with output_path.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "query": query,
                        "system_prompt": system_prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "results": results,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            console.print(f"\n[green]결과가 저장되었습니다: {output_path}[/green]")
        except Exception as e:
            console.print(f"\n[red]결과 저장 실패: {e}[/red]")
