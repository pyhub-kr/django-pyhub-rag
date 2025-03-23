import typer
from rich.console import Console

from pyhub import print_for_main

from .ask import ask
from .describe import describe
from .embed import app as embed_app

app = typer.Typer()
console = Console()

app.add_typer(embed_app)

app.command()(ask)
app.command()(describe)


app.callback(invoke_without_command=True)(print_for_main)
