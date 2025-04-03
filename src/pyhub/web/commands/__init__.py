import contextlib
import getpass
import os
import sys
from pathlib import Path
from typing import Optional

import django
import typer
from django.conf import settings
from django.core.asgi import get_asgi_application
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.utils.autoreload import DJANGO_AUTORELOAD_ENV
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from pyhub import print_for_main

app = typer.Typer()
console = Console()


logo = """
    ██████╗  ██╗   ██╗ ██╗  ██╗ ██╗   ██╗ ██████╗     ██╗    ██╗ ███████╗ ██████╗
    ██╔══██╗ ╚██╗ ██╔╝ ██║  ██║ ██║   ██║ ██╔══██╗    ██║    ██║ ██╔════╝ ██╔══██╗
    ██████╔╝  ╚████╔╝  ███████║ ██║   ██║ ██████╔╝    ██║ █╗ ██║ █████╗   ██████╔╝
    ██╔═══╝    ╚██╔╝   ██╔══██║ ██║   ██║ ██╔══██╗    ██║███╗██║ ██╔══╝   ██╔══██╗
    ██║         ██║    ██║  ██║ ╚██████╔╝ ██████╔╝    ╚███╔███╔╝ ███████╗ ██████╔╝
    ╚═╝         ╚═╝    ╚═╝  ╚═╝  ╚═════╝  ╚═════╝      ╚══╝╚══╝  ╚══════╝ ╚═════╝
"""

app.callback(invoke_without_command=True)(print_for_main(logo))


@app.command()
def run(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload on code changes"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
    is_dev_server: bool = typer.Option(False, "--dev-server", help="Run django dev server"),
    is_disable_check: bool = typer.Option(False, "--disable-check", help="Disable django system check"),
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
    is_debug: bool = typer.Option(False, "--debug"),
):
    """Run the PyHub web server using uvicorn."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        if is_disable_check is False:
            try:
                call_command("check", deploy=False, fail_level="ERROR")
            except SystemCheckError as e:
                console.print(f"[red]{e}[/red]", highlight=False)
                raise typer.Exit(1)

        if is_dev_server:
            args = [f"{host}:{port}", "--skip-checks"]

            if "daphne" not in settings.INSTALLED_APPS:
                # daphne runserver 에서는 --insecure 옵션을 지원하지 않습니다.
                args += ["--insecure"]

            if not reload:
                args.append("--noreload")

            # 메인 프로세스와 auto reload로 구동되는 자식 프로세스를 구별하여, 콘솔 출력
            if DJANGO_AUTORELOAD_ENV not in os.environ:
                console.print(
                    f"Starting PyHub web server on http://{host}:{port} using [green bold]django dev server[/green bold]",
                    style="green",
                )

                console.print("(command) runserver", " ".join(args))

            call_command("runserver", *args)

        else:
            call_command("collectstatic", "--noinput")

            console.print(
                f"Starting PyHub web server on http://{host}:{port} using [green bold]uvicorn[/green bold]",
                style="green",
            )
            application = get_asgi_application()

            import uvicorn

            uvicorn.run(
                application,
                host=host,
                port=port,
                reload=reload,
                workers=workers,
            )


@app.command()
def migrate(
    app_label: Optional[str] = typer.Argument(None),
    migration_name: Optional[str] = typer.Argument(None),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    db_alias: str = typer.Option(
        "default",
        help="migrate를 적용할 database alias",
    ),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """최신 현황까지 데이터베이스 마이그레이션을 실행합니다."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        print_db_config(db_alias)

        args = []

        if app_label is not None:
            args.append(app_label)
        if migration_name is not None:
            args.append(migration_name)

        if db_alias is not None:
            args.extend(("--database", db_alias))
        call_command("migrate", *args)


@app.command()
def showmigrations(
    app_label: list[str] = typer.Argument(None),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    db_alias: str = typer.Option(
        "default",
        help="migrate를 적용할 database alias",
    ),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """마이그레이션 적용 현황을 출력합니다."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        print_db_config(db_alias)

        args = []

        if app_label:
            args.extend(app_label)

        if db_alias is not None:
            args.extend(("--database", db_alias))
        call_command("showmigrations", *args)


@app.command()
def sqlmigrate(
    app_label: str = typer.Argument(...),
    migration_name: str = typer.Argument(...),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    db_alias: str = typer.Option(
        "default",
        help="migrate를 적용할 database alias",
    ),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """장고 쉘을 구동합니다."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        print_db_config(db_alias)

        args = []
        if db_alias is not None:
            args.extend(("--database", db_alias))
        call_command("sqlmigrate", app_label, migration_name, *args)


@app.command()
def createuser(
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """새로운 유저를 생성합니다."""

    username = Prompt.ask("username", default=getpass.getuser())
    password1 = Prompt.ask("password", password=True)
    password2 = Prompt.ask("password (confirm)", password=True)

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        from django.contrib.auth.forms import UserCreationForm

        form = UserCreationForm(
            data={
                "username": username,
                "password1": password1,
                "password2": password2,
            }
        )
        if form.is_valid():
            user = form.save()
            console.print(f"[green]Created user: {user}[/green]")
        else:
            table = Table()
            table.add_column("Field", style="cyan")
            table.add_column("Errors", style="red")
            for field_name, errors in form.errors.items():
                table.add_row(field_name, "\n".join(errors))
            console.print(table)
            raise typer.Exit(1)


@app.command()
def createsuperuser(
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """새로운 슈퍼 유저를 생성합니다."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        call_command("createsuperuser")


@app.command()
def shell(
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """장고 쉘을 구동합니다."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        call_command("shell")


@app.command()
def print_settings(
    settings_names: list[str] = typer.Argument(..., help="출력할 settings 이름을 지정"),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    # format: Optional[] = typer.Option(None, help=""),
    is_debug: bool = typer.Option(False, "--debug"),
):
    """지정 settings 설정을 출력합니다."""

    with pyhub_web_proj(toml_path=toml_path, env_path=env_path, is_debug=is_debug):
        call_command("print_settings", *settings_names)


@contextlib.contextmanager
def pyhub_web_proj(toml_path: Optional[Path], env_path: Optional[Path], is_debug: bool):
    # Find the pyhub.web package path and add it to sys.path
    web_package_path = Path(__file__).parent.parent
    if web_package_path not in sys.path:
        sys.path.insert(0, str(web_package_path))

    os.environ["DEBUG"] = "1" if is_debug else "0"

    if toml_path and toml_path.exists():
        os.environ["TOML_PATH"] = str(toml_path)

    if env_path and env_path.exists():
        os.environ["ENV_PATH"] = str(env_path)

    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
    django.setup()

    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        console.print(
            "[red]PostgreSQL 데이터베이스만 지원됩니다. DATABASE_URL 환경변수를 PostgreSQL URL로 설정해주세요.[/red]"
        )
        sys.exit(1)

    try:
        # 컨텍스트 제공
        yield
    finally:
        # 필요한 정리 작업이 있다면 여기에 구현
        pass


def print_db_config(db_alias: str) -> None:
    config = settings.DATABASES[db_alias]
    if config["HOST"]:
        console.print("[green]using {ENGINE} {HOST}:{PORT}/{NAME}[/green]".format(**config))
    else:
        console.print("[green]using {ENGINE} {NAME}[/green]".format(**config))