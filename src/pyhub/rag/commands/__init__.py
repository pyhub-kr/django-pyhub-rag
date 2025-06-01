import typer
from rich.console import Console

from pyhub import print_for_main

from . import pgvector, sqlite_vec

app = typer.Typer()
console = Console()

# 기존 백엔드별 명령 (하위 호환성)
app.add_typer(sqlite_vec.app)
app.add_typer(pgvector.app)

# 통합 CLI 추가
from ..cli import app as unified_app

# 통합 명령어를 루트 레벨에 병합
for command in unified_app.registered_commands:
    app.command(command.name)(command.callback)


logo = """
    ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██████╗  █████╗  ██████╗
    ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██╔══██╗██╔══██╗██╔════╝
    ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██████╔╝███████║██║  ███╗
    ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██╔══██╗██╔══██║██║   ██║
    ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ██║  ██║██║  ██║╚██████╔╝
    ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝
"""

app.callback(invoke_without_command=True)(print_for_main(logo))
