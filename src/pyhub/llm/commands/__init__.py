import typer
from rich.console import Console

from pyhub import print_for_main

from .agent import app as agent_app
from .ask import ask
from .chat import chat
from .compare import compare
from .describe import describe
from .embed import app as embed_app

app = typer.Typer()
console = Console()

app.add_typer(embed_app, name="embed")
app.add_typer(agent_app, name="agent")

app.command()(ask)
app.command()(describe)
app.command()(chat)
app.command()(compare)


logo = """
    ██████╗  ██╗   ██╗ ██╗  ██╗ ██╗   ██╗ ██████╗     ██╗      ██╗      ███╗   ███╗
    ██╔══██╗ ╚██╗ ██╔╝ ██║  ██║ ██║   ██║ ██╔══██╗    ██║      ██║      ████╗ ████║
    ██████╔╝  ╚████╔╝  ███████║ ██║   ██║ ██████╔╝    ██║      ██║      ██╔████╔██║
    ██╔═══╝    ╚██╔╝   ██╔══██║ ██║   ██║ ██╔══██╗    ██║      ██║      ██║╚██╔╝██║
    ██║         ██║    ██║  ██║ ╚██████╔╝ ██████╔╝    ███████╗ ███████╗ ██║ ╚═╝ ██║
    ╚═╝         ╚═╝    ╚═╝  ╚═╝  ╚═════╝  ╚═════╝     ╚══════╝ ╚══════╝ ╚═╝     ╚═╝
"""

app.callback(invoke_without_command=True)(print_for_main(logo))
