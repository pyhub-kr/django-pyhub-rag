import logging
from pathlib import Path
from typing import Optional

import typer
from django.core.management import call_command
from rich.console import Console

from pyhub import init, print_for_main

app = typer.Typer()
console = Console()


logo = """
    ██████╗ ██╗   ██ ██╗  ██╗ ██╗   ██╗ ██████╗     ██████╗   ██████╗  ██╗  ██╗ ██╗   ██╗
    ██╔══██╗╚██╗ ██╔ ██║  ██║ ██║   ██║ ██╔══██╗    ██╔══██╗ ██╔═══██╗ ██║ ██╔╝ ██║   ██║
    ██████╔╝ ╚████╔╝ ███████║ ██║   ██║ ██████╔╝    ██║  ██║ ██║   ██║ █████╔╝  ██║   ██║
    ██╔═══╝   ╚██╔╝  ██╔══██║ ██║   ██║ ██╔══██╗    ██║  ██║ ██║   ██║ ██╔═██╗  ██║   ██║
    ██║        ██║   ██║  ██║ ╚██████╔╝ ██████╔╝    ██████╔╝ ╚██████╔╝ ██║  ██╗ ╚██████╔╝
    ╚═╝        ╚═╝   ╚═╝  ╚═╝  ╚═════╝  ╚═════╝     ╚═════╝   ╚═════╝  ╚═╝  ╚═╝  ╚═════╝  
"""

app.callback(invoke_without_command=True)(print_for_main(logo))


@app.command()
def run_document_parse_job(
    is_once: bool = typer.Option(False, "--once", help="1회 실행 여부"),
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
    is_verbose: bool = typer.Option(False, "--verbose"),
    is_debug: bool = typer.Option(False, "--debug"),
):
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    args = []

    if is_once:
        args.append("--once")

    if is_debug:
        args.append("--debug")

    call_command("run_document_parse_job", *args)