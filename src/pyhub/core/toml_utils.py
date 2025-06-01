"""TOML 관련 공통 유틸리티 함수들"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

from rich.console import Console

console = Console()


def get_default_toml_content() -> str:
    """기본 TOML 설정 내용을 반환합니다."""
    from pathlib import Path

    # 실제 프롬프트 템플릿 로드
    prompt_base = Path(__file__).parent.parent / "parser" / "templates" / "prompts" / "describe"

    # 이미지 설명 프롬프트
    image_system_prompt = ""
    image_user_prompt = ""
    image_system_path = prompt_base / "image" / "system.md"
    image_user_path = prompt_base / "image" / "user.md"

    if image_system_path.exists():
        image_system_prompt = image_system_path.read_text(encoding="utf-8").strip()
    if image_user_path.exists():
        image_user_prompt = image_user_path.read_text(encoding="utf-8").strip()

    # 테이블 설명 프롬프트
    table_system_prompt = ""
    table_user_prompt = ""
    table_system_path = prompt_base / "table" / "system.md"
    table_user_path = prompt_base / "table" / "user.md"

    if table_system_path.exists():
        table_system_prompt = table_system_path.read_text(encoding="utf-8").strip()
    if table_user_path.exists():
        table_user_prompt = table_user_path.read_text(encoding="utf-8").strip()

    return f'''[env]
# API Keys - 사용할 API 키의 주석을 제거하고 실제 키를 입력하세요
# UPSTAGE_API_KEY = "up_xxxxx..."
# OPENAI_API_KEY = "sk-xxxxx..."
# ANTHROPIC_API_KEY = "sk-ant-xxxxx..."
# GOOGLE_API_KEY = "AIxxxxx...."
# DATABASE_URL = "postgresql://postgres:pw@localhost:5432/postgres"

USER_DEFAULT_TIME_ZONE = "Asia/Seoul"

[prompt_templates.describe_image]
system = """{image_system_prompt}"""
user = """{image_user_prompt}"""

[prompt_templates.describe_table]
system = """{table_system_prompt}"""
user = """{table_user_prompt}"""

'''


def get_editors_for_platform() -> List[str]:
    """플랫폼별 편집기 목록을 반환합니다."""
    if sys.platform.startswith("win"):
        return ["code", "notepad++", "notepad"]
    elif sys.platform.startswith("darwin"):  # macOS
        return ["code", "nvim", "vim", "nano", "emacs", "open"]
    else:  # Linux
        return ["code", "nvim", "vim", "nano", "emacs", "gedit"]


def open_file_with_editor(file_path: Path, verbose: bool = False) -> bool:
    """
    파일을 편집기로 엽니다.

    Args:
        file_path: 열 파일 경로
        verbose: 디버깅 정보 출력 여부

    Returns:
        성공 여부
    """
    # 1. 환경변수에서 에디터 확인
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")

    if verbose:
        console.print(f"[dim]환경변수 에디터: {editor or '없음'}[/dim]")
        console.print(f"[dim]플랫폼: {sys.platform}[/dim]")

    # 2. 플랫폼별 기본 명령 시도
    if not editor:
        if sys.platform.startswith("win"):
            # Windows
            try:
                subprocess.run(["start", str(file_path)], shell=True, check=True)
                console.print("[green]✓ Windows 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            except subprocess.CalledProcessError:
                pass
        elif sys.platform.startswith("darwin"):
            # macOS
            try:
                subprocess.run(["open", str(file_path)], check=True)
                console.print("[green]✓ macOS 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            except subprocess.CalledProcessError:
                pass
        else:
            # Linux
            try:
                subprocess.run(["xdg-open", str(file_path)], check=True)
                console.print("[green]✓ 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            except subprocess.CalledProcessError:
                pass

    # 3. 에디터 명령으로 시도
    if editor:
        editors = [editor]
    else:
        editors = get_editors_for_platform()

    for ed in editors:
        try:
            if verbose:
                console.print(f"[dim]시도 중인 에디터: {ed}[/dim]")

            # 에디터가 존재하는지 먼저 확인
            if ed not in ["notepad", "start", "open", "xdg-open"]:  # 시스템 명령이 아닌 경우
                which_cmd = "where" if sys.platform.startswith("win") else "which"
                result = subprocess.run([which_cmd, ed], capture_output=True, text=True)
                if result.returncode != 0:
                    if verbose:
                        console.print(f"[dim]  → {ed} 에디터를 찾을 수 없음[/dim]")
                    continue  # 에디터가 설치되지 않음
                elif verbose:
                    console.print(f"[dim]  → {ed} 에디터 발견: {result.stdout.strip()}[/dim]")

            # 에디터별 실행 방식 결정
            if sys.platform.startswith("win") and ed == "notepad":
                # Windows notepad
                process = subprocess.Popen([ed, str(file_path)])
            elif ed == "open" and sys.platform.startswith("darwin"):
                # macOS open 명령 (텍스트 모드)
                process = subprocess.Popen(["open", "-t", str(file_path)])
            elif ed == "code":
                # VS Code - 새 창에서 열기
                if verbose:
                    console.print("[dim]  → VS Code를 새 창으로 실행합니다.[/dim]")
                try:
                    process = subprocess.Popen(
                        [ed, "--new-window", str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    # VS Code는 즉시 반환되므로 바로 성공으로 처리
                    import time

                    time.sleep(0.2)  # 잠시 대기하여 실행 확인
                    if process.poll() is None or process.returncode == 0:
                        console.print("[green]✓ VS Code로 파일을 열었습니다.[/green]")
                        return True
                except Exception as e:
                    if verbose:
                        console.print(f"[yellow]VS Code 실행 실패: {e}[/yellow]")
                    continue

            elif ed in ["vim", "nvim", "nano", "emacs"]:
                # 터미널 에디터 - 현재 터미널에서 직접 실행
                if verbose:
                    console.print(f"[dim]  → 터미널 에디터 {ed}를 현재 터미널에서 실행합니다.[/dim]")

                # 현재 터미널에서 직접 실행 (사용자가 편집 완료할 때까지 대기)
                try:
                    result = subprocess.run([ed, str(file_path)])
                    if result.returncode == 0:
                        console.print(f"[green]✓ {ed} 에디터에서 편집을 완료했습니다.[/green]")
                    else:
                        console.print(
                            f"[yellow]경고: {ed} 에디터가 오류와 함께 종료되었습니다 (코드: {result.returncode})[/yellow]"
                        )
                    return True
                except KeyboardInterrupt:
                    console.print("[yellow]\n편집이 중단되었습니다.[/yellow]")
                    return True

            else:
                # 기타 GUI 에디터들
                if verbose:
                    console.print(f"[dim]  → GUI 에디터 {ed}를 백그라운드로 실행합니다.[/dim]")
                try:
                    process = subprocess.Popen(
                        [ed, str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    # 잠시 대기 후 프로세스 상태 확인
                    import time

                    time.sleep(0.2)
                    if process.poll() is None or process.returncode == 0:
                        console.print(f"[green]✓ {ed} 에디터로 파일을 열었습니다.[/green]")
                        return True
                    else:
                        if verbose:
                            console.print(f"[yellow]경고: {ed} 실행 실패 (종료 코드: {process.returncode})[/yellow]")
                        continue
                except Exception as e:
                    if verbose:
                        console.print(f"[yellow]{ed} 실행 중 오류: {e}[/yellow]")
                    continue
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            continue

    # 모든 시도가 실패한 경우
    console.print("[red]오류: 파일을 열 수 있는 에디터를 찾을 수 없습니다.[/red]")
    console.print(f"[dim]시도한 에디터: {', '.join(editors)}[/dim]")
    console.print("[dim]다음 방법들을 시도해보세요:[/dim]")
    console.print("  1. [cyan]VISUAL[/cyan] 또는 [cyan]EDITOR[/cyan] 환경변수 설정:")
    console.print("     [yellow]export EDITOR=nano[/yellow]  # 또는 원하는 에디터")
    console.print("  2. 파일 내용을 직접 확인:")
    console.print("     [cyan]pyhub toml show[/cyan]")
    console.print("  3. 파일을 수동으로 편집:")
    console.print(f"     [yellow]{file_path}[/yellow]")
    return False
