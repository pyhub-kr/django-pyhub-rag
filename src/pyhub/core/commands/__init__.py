import logging
from pathlib import Path
from typing import Optional

import typer
from django.core.management import call_command
from rich.console import Console

from pyhub import init, print_for_main
from pyhub.config import DEFAULT_TOML_PATH

app = typer.Typer(
    pretty_exceptions_show_locals=False,
)


logo = """
    ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗
    ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗
    ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝
    ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗
    ██║        ██║   ██║  ██║╚██████╔╝██████╔╝
    ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
"""


app.callback(invoke_without_command=True)(print_for_main(logo))

console = Console()


def get_default_toml_content() -> str:
    """기본 TOML 템플릿 내용을 반환합니다."""
    from pathlib import Path

    # 실제 프롬프트 템플릿 파일 경로
    prompt_base = Path(__file__).parent.parent.parent / "parser" / "templates" / "prompts" / "describe"

    # 기본 프롬프트 내용 읽기
    image_system = ""
    image_user = ""
    table_system = ""
    table_user = ""

    try:
        image_system_path = prompt_base / "image" / "system.md"
        if image_system_path.exists():
            image_system = image_system_path.read_text(encoding="utf-8").strip()

        image_user_path = prompt_base / "image" / "user.md"
        if image_user_path.exists():
            image_user = image_user_path.read_text(encoding="utf-8").strip()

        table_system_path = prompt_base / "table" / "system.md"
        if table_system_path.exists():
            table_system = table_system_path.read_text(encoding="utf-8").strip()

        table_user_path = prompt_base / "table" / "user.md"
        if table_user_path.exists():
            table_user = table_user_path.read_text(encoding="utf-8").strip()
    except Exception:
        # 파일을 읽을 수 없는 경우 기본값 사용
        image_system = "Analyze the given image and provide a structured output."
        image_user = "Describe this image."
        table_system = "Analyze the given table and extract structured information."
        table_user = "Describe this table."

    return f'''[env]
# UPSTAGE_API_KEY = "up_xxxxx..."
# OPENAI_API_KEY = "sk-xxxxx..."
# ANTHROPIC_API_KEY = "sk-ant-xxxxx..."
# GOOGLE_API_KEY = "AIxxxxx...."

# 무료 PostgreSQL 서비스로서 supabase를 추천합니다. - https://supabase.com
# DATABASE_URL = "postgresql://postgres:pw@localhost:5432/postgres

USER_DEFAULT_TIME_ZONE = "Asia/Seoul"

[prompt_templates.describe_image]
system = """{image_system}"""

user = """{image_user}"""

[prompt_templates.describe_table]
system = """{table_system}"""

user = """{table_user}"""
'''


# toml 서브커맨드 그룹 생성
toml_app = typer.Typer(
    name="toml",
    help="TOML 설정 파일 관리",
    pretty_exceptions_show_locals=False,
    invoke_without_command=True,
)
app.add_typer(toml_app, name="toml")


@toml_app.callback()
def toml_callback(ctx: typer.Context):
    """TOML 설정 파일 관리를 위한 서브커맨드입니다."""
    if ctx.invoked_subcommand is None:
        # 서브커맨드가 없으면 help 출력
        console.print(ctx.get_help())
        raise typer.Exit()


@toml_app.command()
def create(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="기존 파일이 있어도 덮어쓰기",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """새로운 TOML 설정 파일을 생성합니다."""

    # 파일 확장자 확인
    if toml_path.suffix != ".toml":
        console.print(f"[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
        console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
        raise typer.Exit(code=1)

    # 파일 존재 확인
    if toml_path.exists() and not force:
        console.print(f"[red]오류: {toml_path} 파일이 이미 존재합니다.[/red]")
        console.print(f"[dim]다음 중 하나를 선택하세요:[/dim]")
        console.print(f"  • 기존 파일을 덮어쓰려면: [cyan]pyhub toml create --force[/cyan]")
        console.print(f"  • 기존 파일을 편집하려면: [cyan]pyhub toml edit[/cyan]")
        console.print(f"  • 기존 파일을 확인하려면: [cyan]pyhub toml show[/cyan]")
        raise typer.Exit(code=1)

    if toml_path.exists() and force:
        console.print(f"[yellow]경고: {toml_path} 파일을 덮어쓰기 합니다.[/yellow]")

    try:
        # 디렉토리가 없으면 생성
        toml_path.parent.mkdir(parents=True, exist_ok=True)

        # TOML 템플릿 생성 - Django 초기화 없이 직접 생성
        toml_content = get_default_toml_content()

        with toml_path.open("wt", encoding="utf-8") as f:
            f.write(toml_content)

    except PermissionError:
        console.print(f"[red]오류: 파일을 생성할 권한이 없습니다.[/red]")
        console.print(f"[dim]경로: {toml_path}[/dim]")
        raise typer.Exit(code=1)
    except OSError as e:
        console.print(f"[red]오류: 파일을 생성할 수 없습니다.[/red]")
        console.print(f"[dim]상세: {e}[/dim]")
        raise typer.Exit(code=1)
    else:
        console.print(f"[green]✓ 설정 파일이 생성되었습니다: {toml_path}[/green]")
        console.print(f"[dim]다음 명령으로 파일을 편집할 수 있습니다:[/dim]")
        console.print(f"  [cyan]pyhub toml edit[/cyan]")


@toml_app.command()
def show(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """TOML 설정 파일 내용을 출력합니다."""
    # Django 초기화
    init()

    args = [str(toml_path), "--print"]
    call_command("pyhub_toml", *args)


@toml_app.command()
def validate(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """TOML 설정 파일의 유효성을 검증합니다."""
    # Django 초기화
    init()

    args = [str(toml_path), "--test"]
    call_command("pyhub_toml", *args)


@toml_app.command()
def edit(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """TOML 설정 파일을 기본 편집기로 편집합니다."""

    # 파일 확장자 확인
    if toml_path.suffix != ".toml":
        console.print(f"[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
        console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
        raise typer.Exit(code=1)

    # 파일 존재 확인
    if not toml_path.exists():
        console.print(f"[red]오류: {toml_path} 파일이 존재하지 않습니다.[/red]")
        console.print(f"[dim]다음 명령으로 새 설정 파일을 생성할 수 있습니다:[/dim]")
        console.print(f"  [cyan]pyhub toml create[/cyan]")
        raise typer.Exit(code=1)

    console.print(f"[dim]{toml_path} 파일을 편집합니다...[/dim]")

    # 에디터로 파일 열기
    import os
    import sys
    import subprocess

    # 1. 환경변수에서 에디터 확인
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")

    # 2. 플랫폼별 기본 명령 시도
    if not editor:
        if sys.platform.startswith("win"):
            # Windows
            try:
                subprocess.run(["start", str(toml_path)], shell=True, check=True)
                console.print(f"[green]✓ Windows 기본 프로그램으로 파일을 열었습니다.[/green]")
                return
            except subprocess.CalledProcessError:
                pass
        elif sys.platform.startswith("darwin"):
            # macOS
            try:
                subprocess.run(["open", str(toml_path)], check=True)
                console.print(f"[green]✓ macOS 기본 프로그램으로 파일을 열었습니다.[/green]")
                return
            except subprocess.CalledProcessError:
                pass
        else:
            # Linux
            try:
                subprocess.run(["xdg-open", str(toml_path)], check=True)
                console.print(f"[green]✓ 기본 프로그램으로 파일을 열었습니다.[/green]")
                return
            except subprocess.CalledProcessError:
                pass

    # 3. 에디터 명령으로 시도
    if editor:
        editors = [editor]
    else:
        # 플랫폼별 일반적인 에디터들 시도
        if sys.platform.startswith("win"):
            editors = ["code", "notepad++", "notepad"]
        else:
            editors = ["code", "vim", "nano", "emacs", "gedit"]

    for ed in editors:
        try:
            # Windows에서 notepad의 경우 특별 처리
            if sys.platform.startswith("win") and ed == "notepad":
                # notepad는 항상 존재하므로 직접 실행
                subprocess.run([ed, str(toml_path)], check=True)
            else:
                # 다른 에디터들은 일반적인 방식으로 시도
                subprocess.run([ed, str(toml_path)], check=True, 
                             stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            console.print(f"[green]✓ {ed} 에디터로 파일을 열었습니다.[/green]")
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # 모든 시도가 실패한 경우
    console.print(f"[red]오류: 파일을 열 수 있는 에디터를 찾을 수 없습니다.[/red]")
    console.print(f"[dim]시도한 에디터: {', '.join(editors)}[/dim]")
    console.print(f"[dim]VISUAL 또는 EDITOR 환경변수를 설정하거나, 다음 명령으로 파일 내용을 확인하세요:[/dim]")
    console.print(f"  [cyan]pyhub toml show[/cyan]")
    raise typer.Exit(code=1)


@toml_app.command()
def path(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    check_exists: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="파일 존재 여부도 확인",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """TOML 설정 파일의 경로를 출력합니다."""

    # 절대 경로로 변환
    abs_path = toml_path.resolve()

    if check_exists:
        if abs_path.exists():
            console.print(f"[green]✓[/green] {abs_path}")
            if is_verbose:
                # 파일 크기와 수정 시간 표시
                stat = abs_path.stat()
                size = stat.st_size
                mtime = stat.st_mtime
                from datetime import datetime

                modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"[dim]  크기: {size:,} bytes[/dim]")
                console.print(f"[dim]  수정: {modified}[/dim]")
        else:
            console.print(f"[red]✗[/red] {abs_path}")
            console.print(f"[dim]  파일이 존재하지 않습니다[/dim]")

            # 환경변수 정보 표시
            if is_verbose:
                import os

                config_dir = os.environ.get("PYHUB_CONFIG_DIR")
                toml_env = os.environ.get("PYHUB_TOML_PATH")

                if config_dir:
                    console.print(f"[dim]  PYHUB_CONFIG_DIR: {config_dir}[/dim]")
                if toml_env:
                    console.print(f"[dim]  PYHUB_TOML_PATH: {toml_env}[/dim]")

            raise typer.Exit(code=1)
    else:
        # 단순히 경로만 출력 (스크립트 연동용)
        print(abs_path)
