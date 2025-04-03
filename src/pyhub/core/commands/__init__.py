import logging
from pathlib import Path
from typing import Optional

import typer
from django.core.management import call_command
from rich.console import Console

from pyhub import init, print_for_main

app = typer.Typer(
    pretty_exceptions_show_locals=False,
)


logo = """
    ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗
    ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗
    ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝
    ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗
    ██║        ██║   ██║  ██║╚██████╔╝██████╔╝
    ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
"""


app.callback(invoke_without_command=True)(print_for_main(logo))

console = Console()


@app.command()
def toml(
    toml_path: Optional[Path] = typer.Argument(
        Path.home() / ".pyhub.toml",
        help="toml 파일 경로",
    ),
    is_create: bool = typer.Option(
        False,
        "--create",
        "-c",
        help="지정 경로에 toml 설정 파일을 생성합니다.",
    ),
    is_force_create: bool = typer.Option(
        False,
        "--force-create",
        "-f",
        help="지정 경로에 toml 설정 파일을 덮어쓰며 생성합니다. 기존 설정이 유실될 수 있습니다.",
    ),
    is_print: bool = typer.Option(
        False,
        "--print",
        "-p",
        help="지정 경로의 toml 설정 파일을 출력합니다.",
    ),
    is_test: bool = typer.Option(
        False,
        "--test",
        "-t",
        help="지정 경로에 toml 설정 파일을 검증합니다.",
    ),
    is_open: bool = typer.Option(
        False,
        "--open",
        "-o",
        help="지정 경로의 toml 파일을 디폴트 편집기로 엽니다.",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level)

    toml_path = toml_path.resolve()

    args = [str(toml_path)]

    if is_create:
        args.append("--create")
    if is_force_create:
        args.append("--force-create")
    if is_print:
        args.append("--print")
    if is_test:
        args.append("--test")
    if is_open:
        args.append("--open")

    call_command("pyhub_toml", *args)
