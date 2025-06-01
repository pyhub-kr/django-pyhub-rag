import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pyhub import print_for_main
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


# 공통 유틸리티 import
from ..toml_utils import get_default_toml_content, open_file_with_editor

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
        console.print("[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
        console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
        raise typer.Exit(code=1)

    # 파일 존재 확인
    if toml_path.exists() and not force:
        console.print(f"[red]오류: {toml_path} 파일이 이미 존재합니다.[/red]")
        console.print("[dim]다음 중 하나를 선택하세요:[/dim]")
        console.print("  • 기존 파일을 덮어쓰려면: [cyan]pyhub toml create --force[/cyan]")
        console.print("  • 기존 파일을 편집하려면: [cyan]pyhub toml edit[/cyan]")
        console.print("  • 기존 파일을 확인하려면: [cyan]pyhub toml show[/cyan]")
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
        console.print("[red]오류: 파일을 생성할 권한이 없습니다.[/red]")
        console.print(f"[dim]경로: {toml_path}[/dim]")
        raise typer.Exit(code=1)
    except OSError as e:
        console.print("[red]오류: 파일을 생성할 수 없습니다.[/red]")
        console.print(f"[dim]상세: {e}[/dim]")
        raise typer.Exit(code=1)
    else:
        console.print(f"[green]✓ 설정 파일이 생성되었습니다: {toml_path}[/green]")
        console.print("[dim]다음 명령으로 파일을 편집할 수 있습니다:[/dim]")
        console.print("  [cyan]pyhub toml edit[/cyan]")


@toml_app.command()
def show(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """TOML 설정 파일 내용을 출력합니다."""
    # 파일 확장자 확인
    if toml_path.suffix != ".toml":
        console.print("[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
        console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
        raise typer.Exit(code=1)

    # 파일 존재 확인
    if not toml_path.exists():
        console.print(f"[red]오류: {toml_path} 파일이 존재하지 않습니다.[/red]")
        console.print("[dim]다음 명령으로 새 설정 파일을 생성할 수 있습니다:[/dim]")
        console.print("  [cyan]pyhub toml create[/cyan]")
        raise typer.Exit(code=1)

    # 파일 내용 출력
    console.print(f"[dim]{toml_path} 경로의 파일을 출력하겠습니다.[/dim]")
    try:
        with toml_path.open("rt", encoding="utf-8") as f:
            content = f.read()
            print(content)
    except Exception as e:
        console.print("[red]오류: 파일을 읽을 수 없습니다.[/red]")
        console.print(f"[dim]상세: {e}[/dim]")
        raise typer.Exit(code=1)


@toml_app.command()
def validate(
    toml_path: Path = typer.Argument(
        DEFAULT_TOML_PATH,
        help="toml 파일 경로",
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """TOML 설정 파일의 유효성을 검증합니다."""
    # 파일 확장자 확인
    if toml_path.suffix != ".toml":
        console.print("[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
        console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
        raise typer.Exit(code=1)

    # 파일 존재 확인
    if not toml_path.exists():
        console.print(f"[red]오류: {toml_path} 파일이 존재하지 않습니다.[/red]")
        console.print("[dim]다음 명령으로 새 설정 파일을 생성할 수 있습니다:[/dim]")
        console.print("  [cyan]pyhub toml create[/cyan]")
        raise typer.Exit(code=1)

    console.print(f"[dim]{toml_path} 경로의 파일을 확인하겠습니다.[/dim]")

    try:
        # TOML 파일 파싱 시도
        import toml

        with toml_path.open("rt", encoding="utf-8") as f:
            toml_data = toml.load(f)
    except toml.TomlDecodeError as e:
        console.print("[red]오류: 유효하지 않은 TOML 파일입니다.[/red]")
        console.print(f"[dim]상세: {e}[/dim]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print("[red]오류: 파일을 읽을 수 없습니다.[/red]")
        console.print(f"[dim]상세: {e}[/dim]")
        raise typer.Exit(code=1)

    # 환경변수 검증
    env_section = toml_data.get("env", {})
    if not env_section:
        console.print("[red]경고: 등록된 환경변수가 없습니다. (tip: env 항목으로 환경변수를 등록합니다.)[/red]")
    else:
        console.print(f"[green]INFO: 등록된 환경변수 = {', '.join(env_section.keys())}[/green]")

        if "UPSTAGE_API_KEY" not in env_section:
            console.print("[yellow]경고: UPSTAGE_API_KEY 환경변수를 등록해주세요.[/yellow]")

    # 프롬프트 템플릿 검증
    errors = []
    prompt_templates = toml_data.get("prompt_templates", {})

    # 이미지 설명 프롬프트 검증
    describe_image = prompt_templates.get("describe_image", {})
    if "system" not in describe_image:
        errors.append("ERROR: [prompt_templates.describe_image] 의 system 항목이 누락되었습니다.")
    if "user" not in describe_image:
        errors.append("ERROR: [prompt_templates.describe_image] 의 user 항목이 누락되었습니다.")

    # 테이블 설명 프롬프트 검증
    describe_table = prompt_templates.get("describe_table", {})
    if "system" not in describe_table:
        errors.append("ERROR: [prompt_templates.describe_table] 의 system 항목이 누락되었습니다.")
    if "user" not in describe_table:
        errors.append("ERROR: [prompt_templates.describe_table] 의 user 항목이 누락되었습니다.")

    if not errors:
        console.print("[green]INFO: image/table에 대한 시스템/유저 프롬프트 템플릿이 모두 등록되어있습니다.[/green]")
    else:
        for error in errors:
            console.print(f"[red]{error}[/red]")

    if not errors and env_section:
        console.print("\n[green]✓ TOML 파일 검증이 완료되었습니다.[/green]")
    else:
        console.print("\n[yellow]⚠ TOML 파일에 경고사항이 있습니다.[/yellow]")


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
        console.print("[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
        console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
        raise typer.Exit(code=1)

    # 파일 존재 확인
    if not toml_path.exists():
        console.print(f"[red]오류: {toml_path} 파일이 존재하지 않습니다.[/red]")
        console.print("[dim]다음 명령으로 새 설정 파일을 생성할 수 있습니다:[/dim]")
        console.print("  [cyan]pyhub toml create[/cyan]")
        raise typer.Exit(code=1)

    console.print(f"[dim]{toml_path} 파일을 편집합니다...[/dim]")

    # 공통 함수를 사용하여 파일 열기
    if not open_file_with_editor(toml_path, verbose=is_verbose):
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
            console.print("[dim]  파일이 존재하지 않습니다[/dim]")

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
