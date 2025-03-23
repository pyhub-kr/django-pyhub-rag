import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from pyhub import get_version, init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum, LLMVendorEnum

console = Console()


def ask(
    query: Optional[str] = typer.Argument(None, help="질의 내용"),
    vendor: LLMVendorEnum = typer.Option(
        LLMVendorEnum.OPENAI,
        "--vendor",
        "-v",
        help="LLM 벤더",
    ),
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
        "-m",
        help="멀티 턴 대화",
    ),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        "--toml-file",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    is_print_version: bool = typer.Option(False, "--version", help="현재 패키지 버전 출력"),
):
    """LLM에 질의하고 응답을 출력합니다."""

    if is_print_version:
        console.print(get_version())
        raise typer.Exit()

    if query is None:
        console.print("[bold red]Error: missing query text[/bold red]")
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
        log_level = logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    if is_verbose:
        table = Table()
        table.add_column("설정", style="cyan")
        table.add_column("값", style="green")
        table.add_row("vendor", vendor.value)
        table.add_row("model", model.value)
        table.add_row("context", context)
        table.add_row("system prompt", system_prompt)
        table.add_row("user prompt", query)
        table.add_row("temperature", str(temperature))
        table.add_row("max_tokens", str(max_tokens))
        table.add_row("멀티 턴 여부", "O" if is_multi else "X")
        table.add_row("toml_path", f"{toml_path.resolve()} ({"Found" if toml_path.exists() else "Not found"})")
        table.add_row("env_path", f"{env_path.resolve()} ({"Found" if env_path.exists() else "Not found"})")
        console.print(table)

    llm = LLM.create(
        model=model.value,
        vendor=vendor.value,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if not is_multi:
        for chunk in llm.ask(query, stream=True):
            console.print(chunk.text, end="")
        console.print()

    else:
        console.print("Human:", query)

        while query:
            console.print("AI:", end=" ")
            for chunk in llm.ask(query, stream=True):
                console.print(chunk.text, end="")
            console.print()

            query = Prompt.ask("Human")