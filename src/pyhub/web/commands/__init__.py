import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """PyHub RAG CLI tool"""
    if ctx.invoked_subcommand is None:
        console.print(
            """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██╗    ██╗███████╗██████╗ 
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██║    ██║██╔════╝██╔══██╗
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██║ █╗ ██║█████╗  ██████╔╝
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██║███╗██║██╔══╝  ██╔══██╗
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ╚███╔███╔╝███████╗██████╔╝
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝      ╚══╝╚══╝ ╚══════╝╚═════╝ 
        """,
            style="bold white",
        )
        console.print("Welcome to PyHub Web CLI!", style="green")


@app.command()
def run(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload on code changes"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Logging level"),
):
    """Run the PyHub web server using uvicorn."""
    import uvicorn

    console.print(f"Starting PyHub web server on http://{host}:{port}", style="green")

    # Find the pyhub.web package path and add it to sys.path
    web_package_path = Path(__file__).parent.parent
    if web_package_path not in sys.path:
        sys.path.insert(0, str(web_package_path))

    uvicorn.run(
        "pyhub.web.config.asgi:application",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )
