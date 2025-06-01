import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from pyhub import init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum

console = Console()


def ask(
    ctx: typer.Context,
    query: Optional[str] = typer.Argument(None, help="질의 내용"),
    model: LLMChatModelEnum = typer.Option(
        LLMChatModelEnum.GPT_4O_MINI,
        "--model",
        "-m",
        help="LLM Chat 모델. LLM 벤더에 맞게 지정해주세요.",
    ),
    context: str = typer.Option(None, help="LLM에 제공할 컨텍스트"),
    system_prompt: str = typer.Option(None, help="LLM에 사용할 시스템 프롬프트"),
    system_prompt_path: str = typer.Option(
        "system_prompt.txt",
        help="시스템 프롬프트가 포함된 파일 경로",
    ),
    temperature: float = typer.Option(0.2, help="LLM 응답의 온도 설정 (0.0-2.0, 높을수록 다양한 응답)"),
    max_tokens: int = typer.Option(1000, help="응답의 최대 토큰 수"),
    is_multi: bool = typer.Option(
        False,
        "--multi",
        help="멀티 턴 대화",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="JSON 형식으로 출력 (구조화된 응답)",
    ),
    schema_path: Optional[Path] = typer.Option(
        None,
        "--schema",
        help="JSON Schema 파일 경로 (구조화된 응답 형식 정의). "
        "OpenAI와 Upstage는 완전한 구조화된 출력을 지원하며, "
        "Anthropic, Google, Ollama는 프롬프트 엔지니어링을 통한 제한적 지원만 제공합니다.",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="응답을 저장할 파일 경로",
    ),
    template_name: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="프롬프트 템플릿 이름 (toml 파일에서 로드)",
    ),
    show_cost: bool = typer.Option(
        False,
        "--cost",
        help="예상 비용 표시 (주의: Upstage 모델은 스트리밍 모드에서 지원 안 됨)",
    ),
    show_stats: bool = typer.Option(
        False,
        "--stats",
        help="토큰 사용량 및 응답 시간 통계 표시",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    no_stream: bool = typer.Option(
        False,
        "--no-stream",
        help="스트리밍 비활성화 (기본: 스트리밍 활성)",
    ),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """LLM에 질의하고 응답을 출력합니다.

    Examples:
        # 기본 사용 (스트리밍)
        pyhub.llm ask "What is Python?"

        # 비스트리밍 모드 (Upstage에서 비용 정보 필요 시)
        pyhub.llm ask "Hello" --no-stream --cost

        # 파일로 저장
        pyhub.llm ask "Explain AI" --output response.txt

        # 템플릿 사용
        pyhub.llm ask "Fix this code" --template code_review

        # JSON 형식 출력
        pyhub.llm ask "List 3 colors" --json
    """

    if query is None:
        if sys.stdin.isatty():
            # stdin이 터미널인 경우 (파이프라인이 아닌 경우) - help 출력
            console.print(ctx.get_help())
            raise typer.Exit()
        else:
            # stdin에서 입력을 받는 경우
            console.print("[red]오류: 질문이 제공되지 않았습니다.[/red]")
            console.print('[dim]사용법: pyhub.llm ask "질문"[/dim]')
            console.print('[dim]또는: echo "컨텍스트" | pyhub.llm ask "질문"[/dim]')
            raise typer.Exit(1)

    # Use stdin as context if available and no context argument was provided
    if context is None and not sys.stdin.isatty():
        context = sys.stdin.read().strip()

    # Handle system prompt options
    if system_prompt_path:
        try:
            with open(system_prompt_path, "r") as f:
                system_prompt = f.read().strip()
        except IOError:
            pass

    if context:
        system_prompt = ((system_prompt or "") + "\n\n" + f"<context>{context}</context>").strip()

    # if system_prompt:
    #     console.print(f"# System prompt\n\n{system_prompt}\n\n----\n\n", style="blue")

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING  # Only show warnings and errors when not verbose
    init(debug=is_verbose, log_level=log_level)

    # 템플릿 로드
    if template_name:
        try:
            import toml

            from pyhub.config import Config

            toml_path = Config.get_default_toml_path()
            if toml_path.exists():
                with toml_path.open("r", encoding="utf-8") as f:
                    config = toml.load(f)
                    templates = config.get("prompt_templates", {}).get(template_name, {})
                    if templates:
                        system_prompt = templates.get("system", system_prompt)
                        if "user" in templates and "{query}" in templates["user"]:
                            query = templates["user"].format(query=query)
                    else:
                        console.print(f"[yellow]경고: 템플릿 '{template_name}'을 찾을 수 없습니다.[/yellow]")
        except Exception as e:
            console.print(f"[yellow]템플릿 로드 오류: {e}[/yellow]")

    # JSON Schema 로드
    choices = None
    if schema_path and schema_path.exists():
        try:
            import json

            with schema_path.open("r", encoding="utf-8") as f:
                choices = json.load(f)
        except Exception as e:
            console.print(f"[red]JSON Schema 파일 읽기 오류: {e}[/red]")
            raise typer.Exit(1)

    if is_verbose:
        table = Table()
        table.add_column("설정", style="cyan")
        table.add_column("값", style="green")
        table.add_row("model", model)
        table.add_row("context", context)
        table.add_row("system prompt", system_prompt)
        table.add_row("user prompt", query)
        table.add_row("temperature", str(temperature))
        table.add_row("max_tokens", str(max_tokens))
        table.add_row("멀티 턴 여부", "O" if is_multi else "X")
        table.add_row("JSON 출력", "O" if output_json else "X")
        if schema_path:
            table.add_row("JSON Schema", str(schema_path))
        console.print(table)

    llm = LLM.create(
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if is_verbose:
        console.print(f"Using llm {llm.model}")

    import time

    start_time = time.time()

    if not is_multi:
        response_text = ""
        usage = None

        if is_verbose:
            console.print(f"[dim]디버그: 모델={model.value}, show_cost={show_cost}, show_stats={show_stats}[/dim]")

        if output_json or choices:
            # 구조화된 응답
            response = llm.ask(query, choices=choices, enable_cache=enable_cache)
            usage = response.usage if hasattr(response, "usage") else None
            if output_json:
                import json
                from dataclasses import asdict, is_dataclass

                # dataclass를 dict로 변환
                if is_dataclass(response):
                    response_dict = asdict(response)
                    # Usage의 total property를 수동으로 추가
                    if "usage" in response_dict and response_dict["usage"]:
                        response_dict["usage"]["total"] = response.usage.total
                elif hasattr(response, "model_dump"):
                    response_dict = response.model_dump()
                else:
                    response_dict = response

                # 비용 정보 추가 (요청된 경우)
                if show_cost and usage:
                    try:
                        from pyhub.llm.utils.pricing import calculate_cost

                        cost = calculate_cost(model.value, usage.input, usage.output)
                        response_dict["cost"] = {
                            "input_cost": cost["input_cost"],
                            "output_cost": cost["output_cost"],
                            "total_cost": cost["total_cost"],
                            "total_cost_krw": cost["total_cost"] * 1300,
                        }
                    except Exception as e:
                        if is_verbose:
                            console.print(f"[yellow]비용 계산 실패: {e}[/yellow]")

                response_text = json.dumps(response_dict, ensure_ascii=False, indent=2)
                console.print(response_text)
            else:
                response_text = str(response)
                console.print(response_text)
        else:
            # 일반 텍스트 응답
            if no_stream:
                # 비스트리밍 모드
                if is_verbose:
                    console.print("[dim]디버그: 비스트리밍 모드 사용[/dim]")
                response = llm.ask(query, stream=False, enable_cache=enable_cache)
                response_text = response.text
                usage = response.usage
                console.print(response_text)
            else:
                # 스트리밍 모드 (기본)
                if is_verbose:
                    console.print("[dim]디버그: 스트리밍 시작...[/dim]")
                for chunk in llm.ask(query, stream=True, enable_cache=enable_cache):
                    if chunk.text:  # 텍스트가 있는 경우에만 출력
                        console.print(chunk.text, end="")
                        response_text += chunk.text
                    if hasattr(chunk, "usage") and chunk.usage:
                        if is_verbose:
                            console.print(
                                f"\n[dim]디버그: Usage 발견 - input: {chunk.usage.input}, output: {chunk.usage.output}[/dim]"
                            )
                        usage = chunk.usage
                console.print()

        # 응답 시간 계산
        elapsed_time = time.time() - start_time

        # 파일로 저장
        if output_path:
            try:
                with output_path.open("w", encoding="utf-8") as f:
                    f.write(response_text)
                console.print(f"[green]응답이 저장되었습니다: {output_path}[/green]")
            except Exception as e:
                console.print(f"[red]파일 저장 오류: {e}[/red]")

        # 통계 표시
        if show_stats and usage:
            stats_table = Table(title="통계")
            stats_table.add_column("항목", style="cyan")
            stats_table.add_column("값", style="green")
            stats_table.add_row("입력 토큰", str(usage.input))
            stats_table.add_row("출력 토큰", str(usage.output))
            stats_table.add_row("총 토큰", str(usage.total))
            stats_table.add_row("응답 시간", f"{elapsed_time:.2f}초")
            console.print(stats_table)

        # 비용 표시
        if show_cost:
            if is_verbose:
                console.print(f"[dim]디버그: show_cost={show_cost}, usage={usage}[/dim]")
            if usage:
                try:
                    from pyhub.llm.utils.pricing import calculate_cost

                    cost = calculate_cost(model, usage.input, usage.output)
                    cost_table = Table(title="예상 비용")
                    cost_table.add_column("항목", style="cyan")
                    cost_table.add_column("값", style="green")
                    cost_table.add_row("입력 비용", f"$ {cost['input_cost']:.6f}")
                    cost_table.add_row("출력 비용", f"$ {cost['output_cost']:.6f}")
                    cost_table.add_row("총 비용", f"$ {cost['total_cost']:.6f}")
                    cost_table.add_row("원화 환산", f"₩ {cost['total_cost'] * 1300:.6f}")
                    console.print(cost_table)
                except Exception as e:
                    console.print(f"[red]비용 계산 오류: {e}[/red]")
                    if is_verbose:
                        import traceback

                        console.print(f"[yellow]{traceback.format_exc()}[/yellow]")
            else:
                # 모델별 상세한 안내 메시지
                if "upstage" in model.value.lower() or "solar" in model.value.lower():
                    console.print(
                        "[yellow]경고: Upstage 모델은 스트리밍 모드에서 토큰 사용량 정보를 제공하지 않습니다.[/yellow]"
                    )
                    console.print(
                        "[dim]💡 팁: 비용 정보를 보려면 --no-stream 옵션을 사용하여 비스트리밍 모드로 실행하세요.[/dim]"
                    )
                else:
                    console.print(
                        "[yellow]경고: 토큰 사용량 정보를 가져올 수 없습니다. (캐시된 응답이거나 스트리밍 사용량이 지원되지 않는 모델일 수 있습니다)[/yellow]"
                    )

    else:
        console.print("Human:", query)

        while query:
            console.print("AI:", end=" ")
            if no_stream:
                response = llm.ask(query, stream=False, enable_cache=enable_cache)
                console.print(response.text)
            else:
                for chunk in llm.ask(query, stream=True, enable_cache=enable_cache):
                    console.print(chunk.text, end="")
                console.print()

            query = Prompt.ask("Human")
