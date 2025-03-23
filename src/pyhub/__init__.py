from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

import typer
from rich.console import Console
from rich.table import Table

from .init import PromptTemplates, init, load_envs, load_toml, make_settings

console = Console()


def get_version() -> str:
    try:
        return version("django-pyhub-rag")
    except PackageNotFoundError:
        return "not found"


def print_for_main(
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
        print_logo()


def print_copyright() -> None:
    msg = f" © {datetime.now().year} 파이썬사랑방 (버그리포트, 기능제안, 컨설팅/교육 문의 : me@pyhub.kr)"

    console.print(f"\n[dim]{msg}[/dim]")


def print_help(ctx: typer.Context) -> None:
    console.print(ctx.get_help())
    print_copyright()
    raise typer.Exit()


def print_logo() -> None:
    logo = """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██████╗  █████╗  ██████╗ 
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██╔══██╗██╔══██╗██╔════╝ 
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██████╔╝███████║██║  ███╗
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██╔══██╗██╔══██║██║   ██║
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ██║  ██║██║  ██║╚██████╔╝
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ 
    """

    console.print(logo, style="bold white")
    console.print(f"Welcome to PyHub RAG CLI! {get_version()} (Documents : https://rag.pyhub.kr)", style="green")

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("지원 명령", style="cyan")
    table.add_column("설명", style="green")

    # Add rows to the table
    table.add_row("pyhub.parser upstage --help", "명령 1번에 PDF 파싱부터 이미지 설명 자동 작성")
    table.add_row("pyhub.llm ask --help", "다양한 LLM 모델에 대한 질의")
    table.add_row("pyhub.llm embed --help", "jsonl 파일에 대한 임베딩 생성")
    table.add_row("pyhub.rag sqlite-vec --help", "SQLite 벡터스토어 명령 (테이블 생성, 데이터 저장, 유사 문서 검색)")
    console.print(table)

    # arg: str = sys.argv[0]
    # matches: list[str] = re.findall(r"pyhub[./\\]+([a-zA-Z0-9_]+)", arg)
    # if matches:
    #     module_name = matches[-1]

    console.print(
        "\n장고와 함께 웹 기반의 PDF 지식 저장소를 손쉽게 구축하실 수 있습니다. - 파이썬사랑방 (me@pyhub.kr)",
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
