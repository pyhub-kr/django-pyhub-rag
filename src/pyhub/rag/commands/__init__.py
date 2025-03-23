import typer
from rich.console import Console

from pyhub import print_for_main

from . import sqlite_vec

app = typer.Typer()
console = Console()

app.add_typer(sqlite_vec.app)


app.callback(invoke_without_command=True)(print_for_main)
