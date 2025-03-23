import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pyhub import get_version, print_for_main

app = typer.Typer()
console = Console()


app.callback(invoke_without_command=True)(print_for_main)


@app.command()
def run(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload on code changes"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
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
    is_print_version: bool = typer.Option(False, "--version", help="현재 패키지 버전 출력"),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """Run the PyHub web server using uvicorn."""
    import uvicorn

    if is_print_version:
        console.print(get_version())
        raise typer.Exit()

    if toml_path and toml_path.exists():
        os.environ["TOML_PATH"] = str(toml_path)

    if env_path and env_path.exists():
        os.environ["ENV_PATH"] = str(env_path)

    os.environ["DEBUG"] = "1" if is_debug else "0"

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
    )
