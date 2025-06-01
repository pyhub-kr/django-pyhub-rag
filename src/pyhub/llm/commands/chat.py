import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

from pyhub import init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum

console = Console()


def chat(
    model: LLMChatModelEnum = typer.Option(
        LLMChatModelEnum.GPT_4O_MINI,
        "--model",
        "-m",
        help="LLM Chat 모델",
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
        help="응답 온도 (0.0-2.0)",
    ),
    max_tokens: int = typer.Option(
        2000,
        "--max-tokens",
        help="최대 토큰 수",
    ),
    history_path: Optional[Path] = typer.Option(
        None,
        "--history",
        help="대화 히스토리 저장 경로",
    ),
    show_cost: bool = typer.Option(
        False,
        "--cost",
        help="각 응답의 비용 표시",
    ),
    markdown_mode: bool = typer.Option(
        True,
        "--markdown/--no-markdown",
        help="마크다운 렌더링 사용",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """대화형 LLM 세션을 시작합니다."""

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    # 세션 정보 표시
    console.print("\n[bold blue]💬 LLM Chat Session[/bold blue]")
    console.print(f"[dim]모델: {model.value} | 온도: {temperature} | 최대 토큰: {max_tokens}[/dim]")
    if system_prompt:
        console.print(
            f"[dim]시스템 프롬프트: {system_prompt[:50]}...[/dim]"
            if len(system_prompt) > 50
            else f"[dim]시스템 프롬프트: {system_prompt}[/dim]"
        )
    console.print("[dim]종료하려면 'exit', 'quit', Ctrl+C 또는 Ctrl+D를 입력하세요.[/dim]")
    console.print("[dim]대화를 초기화하려면 'clear'를 입력하세요.[/dim]")
    console.print("[dim]현재 설정을 보려면 'settings'를 입력하세요.[/dim]")
    console.print()

    # 초기 시스템 프롬프트 저장
    base_system_prompt = system_prompt or ""

    # 대화 히스토리
    messages = []
    if history_path and history_path.exists():
        try:
            import json

            with history_path.open("r", encoding="utf-8") as f:
                messages = json.load(f)
                console.print(f"[green]히스토리 로드: {len(messages)} 메시지[/green]\n")
        except Exception as e:
            console.print(f"[yellow]히스토리 로드 실패: {e}[/yellow]\n")

    # 총 사용량 추적
    from pyhub.llm.types import Usage

    total_usage = Usage()
    turn_count = 0

    # 대화 루프
    while True:
        try:
            # 사용자 입력
            try:
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            except EOFError:
                # Ctrl-D 처리
                console.print("\n[yellow]대화를 종료합니다...[/yellow]")
                break

            # 특수 명령 처리
            if user_input.lower() in ["exit", "quit", "bye"]:
                break
            elif user_input.lower() == "clear":
                messages = []
                total_usage = Usage()
                turn_count = 0
                console.print("[yellow]대화가 초기화되었습니다.[/yellow]")
                continue
            elif user_input.lower() == "settings":
                settings_table = Table(title="현재 설정")
                settings_table.add_column("항목", style="cyan")
                settings_table.add_column("값", style="green")
                settings_table.add_row("모델", model.value)
                settings_table.add_row("온도", str(temperature))
                settings_table.add_row("최대 토큰", str(max_tokens))
                settings_table.add_row("시스템 프롬프트", system_prompt or "(없음)")
                settings_table.add_row("대화 턴", str(turn_count))
                settings_table.add_row("총 입력 토큰", str(total_usage.input))
                settings_table.add_row("총 출력 토큰", str(total_usage.output))
                console.print(settings_table)
                continue

            # AI 응답
            console.print("\n[bold green]AI[/bold green]: ", end="")

            response_text = ""
            usage = None

            # 대화 컨텍스트를 시스템 프롬프트에 포함
            conversation_context = ""
            if messages:
                conversation_context = "\n\n대화 히스토리:\n"
                for msg in messages[-10:]:  # 최근 10개 메시지만 포함
                    role = "Human" if msg["role"] == "user" else "AI"
                    conversation_context += f"{role}: {msg['content']}\n"

            # LLM 재생성 with 대화 컨텍스트
            current_system_prompt = base_system_prompt
            if conversation_context:
                current_system_prompt = base_system_prompt + conversation_context

            llm = LLM.create(
                model=model,
                system_prompt=current_system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # 스트리밍 응답
            for chunk in llm.ask(user_input, stream=True, enable_cache=enable_cache):
                if markdown_mode and "\n" in chunk.text:
                    # 마크다운 모드에서는 전체 응답을 모아서 렌더링
                    response_text += chunk.text
                else:
                    console.print(chunk.text, end="")
                    response_text += chunk.text

                if hasattr(chunk, "usage") and chunk.usage:
                    usage = chunk.usage

            # 마크다운 렌더링
            if markdown_mode and response_text:
                console.print()  # 줄바꿈
                console.print(Markdown(response_text))
            else:
                console.print()  # 줄바꿈

            # 메시지 히스토리 업데이트
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": response_text})
            turn_count += 1

            # 사용량 업데이트
            if usage:
                total_usage += usage

                # 비용 표시
                if show_cost:
                    try:
                        from pyhub.llm.utils.pricing import calculate_cost

                        cost = calculate_cost(model.value, usage.input, usage.output)
                        console.print(
                            f"[dim]토큰: 입력 {usage.input}, 출력 {usage.output} | "
                            f"비용: ${cost['total_cost']:.6f} (₩{cost['total_cost'] * 1300:.0f})[/dim]"
                        )
                    except:
                        pass

            # 히스토리 저장
            if history_path:
                try:
                    import json

                    history_path.parent.mkdir(parents=True, exist_ok=True)
                    with history_path.open("w", encoding="utf-8") as f:
                        json.dump(messages, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    if is_verbose:
                        console.print(f"[yellow]히스토리 저장 실패: {e}[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[yellow]대화를 종료합니다...[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]오류: {e}[/red]")
            if is_verbose:
                console.print_exception()

    # 세션 종료
    console.print("\n[bold blue]세션 종료[/bold blue]")
    if turn_count > 0:
        stats_table = Table(title="세션 통계")
        stats_table.add_column("항목", style="cyan")
        stats_table.add_column("값", style="green")
        stats_table.add_row("대화 턴", str(turn_count))
        stats_table.add_row("총 입력 토큰", str(total_usage.input))
        stats_table.add_row("총 출력 토큰", str(total_usage.output))

        if show_cost:
            try:
                from pyhub.llm.utils.pricing import calculate_cost

                total_cost = calculate_cost(model.value, total_usage.input, total_usage.output)
                stats_table.add_row("총 비용", f"${total_cost['total_cost']:.4f}")
                stats_table.add_row("원화 환산", f"₩{total_cost['total_cost'] * 1300:.0f}")
            except:
                pass

        console.print(stats_table)

    console.print("\n👋 안녕히 가세요!")
