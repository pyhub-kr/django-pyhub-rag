import typer
from rich.console import Console

from pyhub import print_for_main

from .upstage import upstage
from .upstage_extract import upstage_extract

app = typer.Typer()
console = Console()

app.command()(upstage)
app.command()(upstage_extract)


logo = """
    ██████╗  ██╗   ██╗ ██╗  ██╗ ██╗   ██╗ ██████╗     ██████╗   █████╗ ██████╗ ███████╗███████╗██████╗
    ██╔══██╗ ╚██╗ ██╔╝ ██║  ██║ ██║   ██║ ██╔══██╗    ██╔══██╗ ██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗
    ██████╔╝  ╚████╔╝  ███████║ ██║   ██║ ██████╔╝    ██████╔╝ ███████║██████╔╝███████╗█████╗  ██████╔╝
    ██╔═══╝    ╚██╔╝   ██╔══██║ ██║   ██║ ██╔══██╗    ██╔═══╝  ██╔══██║██╔══██╗╚════██║██╔══╝  ██╔══██╗
    ██║         ██║    ██║  ██║ ╚██████╔╝ ██████╔╝    ██║      ██║  ██║██║  ██║███████║███████╗██║  ██║
    ╚═╝         ╚═╝    ╚═╝  ╚═╝  ╚═════╝  ╚═════╝     ╚═╝      ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
"""

app.callback(invoke_without_command=True)(print_for_main(logo))
