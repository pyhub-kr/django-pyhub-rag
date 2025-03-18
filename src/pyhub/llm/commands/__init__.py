import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pyhub import get_version, init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum

# from . import embed, sqlite_vec

app = typer.Typer()
console = Console()

# app.add_typer(embed.app)
# app.add_typer(sqlite_vec.app)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    is_print_version: bool = typer.Option(False, "--version", help="현재 패키지 버전 출력"),
):
    """PyHub RAG CLI tool"""

    if is_print_version:
        console.print(get_version())
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print(
            """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██╗     ██╗     ███╗   ███╗
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██║     ██║     ████╗ ████║
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██║     ██║     ██╔████╔██║
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██║     ██║     ██║╚██╔╝██║
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ███████╗███████╗██║ ╚═╝ ██║
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚══════╝╚══════╝╚═╝     ╚═╝
        """
        )
        console.print(f"Welcome to PyHub LLM CLI! {get_version()}")
        console.print(
            "\n장고와 함께 웹 기반의 PDF 지식 저장소를 손쉽게 구축하실 수 있습니다. - 파이썬사랑방 (me@pyhub.kr)",
            style="green",
        )


@app.command()
def ask(
    query: Optional[str] = typer.Argument(None, help="유사한 문서를 검색할 텍스트"),
    model: LLMChatModelEnum = typer.Option(
        LLMChatModelEnum.GPT_4O,
        "--model",
        "-m",
        help="임베딩 모델",
    ),
    context: str = typer.Option(None, help="LLM에 제공할 컨텍스트"),
    system_prompt: str = typer.Option(None, help="LLM에 사용할 시스템 프롬프트"),
    system_prompt_path: str = typer.Option(
        "system_prompt.txt",
        help="시스템 프롬프트가 포함된 파일 경로",
    ),
    temperature: float = typer.Option(0.2, help="LLM 응답의 온도 설정 (0.0-2.0, 높을수록 다양한 응답)"),
    max_tokens: int = typer.Option(1000, help="응답의 최대 토큰 수"),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    is_print_version: bool = typer.Option(False, "--version", help="현재 패키지 버전 출력"),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
):
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
    init(debug=True, log_level=log_level, env_path=env_path)

    llm = LLM.create(
        model.value,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    for chunk in llm.ask(query, stream=True):
        console.print(chunk.text, end="")
    console.print()
