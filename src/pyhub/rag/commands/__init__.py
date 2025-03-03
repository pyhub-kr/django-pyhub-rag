import typer
from rich.console import Console

from . import sqlite_vec

app = typer.Typer()
console = Console()

app.add_typer(sqlite_vec.sqlite_vec_app)


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
        """,
            style="bold blue",
        )
        console.print("Welcome to PyHub RAG CLI!", style="green")
