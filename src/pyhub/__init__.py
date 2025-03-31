from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

import typer
from rich.console import Console

from .init import PromptTemplates, init, load_envs, load_toml, make_settings

console = Console()


DEFAULT_LOGO = """
    ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗
    ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗
    ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝
    ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗
    ██║        ██║   ██║  ██║╚██████╔╝██████╔╝
    ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
"""


def get_version() -> str:
    try:
        return version("django-pyhub-rag")
    except PackageNotFoundError:
        return "not found"


def print_for_main(logo: str):
    def wrap(
        ctx: typer.Context,
        is_help: bool = typer.Option(False, "--help", "-h", help="도움말 메시지 출력"),
        is_print_version: bool = typer.Option(False, "--version", help="현재 패키지 버전 출력"),
    ):
        if is_print_version:
            console.print(get_version())
            raise typer.Exit()

        if is_help:
            print_help(ctx)
            raise typer.Exit()

        if ctx.invoked_subcommand is None:
            print_logo(logo)
            print_help(ctx)

    return wrap


def print_copyright() -> None:
    msg = f" © {datetime.now().year} 파이썬사랑방 (버그리포트, 기능제안, 컨설팅/교육 문의 : me@pyhub.kr)"

    console.print(f"[dim]{msg}[/dim]")


def print_help(ctx: typer.Context) -> None:
    console.print(ctx.get_help())
    print_copyright()
    raise typer.Exit()


def print_logo(logo: Optional[str] = None) -> None:
    console.print(logo or DEFAULT_LOGO, style="bold white")
    console.print(f"Welcome to PyHub RAG CLI! {get_version()} (Documents : https://rag.pyhub.kr)", style="green")

    # arg: str = sys.argv[0]
    # matches: list[str] = re.findall(r"pyhub[./\\]+([a-zA-Z0-9_]+)", arg)
    # if matches:
    #     module_name = matches[-1]

    console.print(
        "\n장고와 함께 웹 기반의 문서 지식 저장소를 손쉽게 구축하실 수 있습니다.",
        style="green",
    )


__all__ = [
    "init",
    "PromptTemplates",
    "load_envs",
    "load_toml",
    "get_version",
    "make_settings",
    "print_for_main",
    "print_copyright",
]
