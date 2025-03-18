import typer
from rich.console import Console

from . import sqlite_vec
from ... import get_version

app = typer.Typer()
console = Console()

app.add_typer(sqlite_vec.app)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """PyHub RAG CLI tool"""
    if ctx.invoked_subcommand is None:
        console.print(
            """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██████╗  █████╗  ██████╗ 
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██╔══██╗██╔══██╗██╔════╝ 
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██████╔╝███████║██║  ███╗
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██╔══██╗██╔══██║██║   ██║
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ██║  ██║██║  ██║╚██████╔╝
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝
                """
        )
        console.print(f"Welcome to PyHub RAG CLI! {get_version()}")
        console.print(
            "\n장고와 함께 웹 기반의 PDF 지식 저장소를 손쉽게 구축하실 수 있습니다. - 파이썬사랑방 (me@pyhub.kr)",
            style="green",
        )
