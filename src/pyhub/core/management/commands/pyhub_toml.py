import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

from django.template.loader import get_template
from django_rich.management import RichCommand
from django_typer.management import TyperCommand
from typer import Option, BadParameter, Exit, Argument

from pyhub.parser.upstage.parser import ImageDescriptor


class Command(RichCommand, TyperCommand):
    def handle(
        self,
        toml_path: Annotated[Optional[Path], Argument(help="toml 파일 경로. 디폴트: ~/.pyhub.toml")] = None,
        is_create: Annotated[bool, Option("--create", "-c", help="지정 경로에 toml 설정 파일을 생성합니다.")] = False,
        is_force_create: Annotated[
            bool,
            Option(
                "--force-create",
                "-f",
                help="지정 경로에 toml 설정 파일을 덮어쓰며 생성합니다. 기존 설정이 유실될 수 있습니다.",
            ),
        ] = False,
        is_print: Annotated[bool, Option("--print", "-p", help="지정 경로의 toml 설정 파일을 출력합니다.")] = False,
        is_test: Annotated[bool, Option("--test", "-t", help="지정 경로의 toml 파일을 검증합니다.")] = False,
        is_open: Annotated[
            bool, Option("--open", "-o", help="지정 경로의 toml 파일을 디폴트 편집기로 엽니다.")
        ] = False,
    ):
        if toml_path is None:
            toml_path = Path.home() / ".pyhub.toml"

        if toml_path.suffix != ".toml":
            raise BadParameter("확장자를 .toml로 지정해주세요.")

        if is_create or is_force_create:
            if toml_path.exists():
                if is_force_create:
                    self.console.print(f"[red]{toml_path} 경로의 파일을 덮어쓰기 합니다.[/red]")
                else:
                    raise BadParameter(f"{toml_path} 경로에 파일이 이미 있습니다.")

            try:
                with toml_path.open("wt", encoding="utf-8") as f:
                    f.write(self._get_toml_str())
            except Exception as e:
                self.console.print(f"[red]{e}[/red]")
                raise Exit(code=1)
            else:
                self.console.print(
                    f"[green]{toml_path} 경로에 설정 파일 초안을 생성했습니다. 목적에 맞게 수정해주세요.[/green]"
                )

            raise Exit(code=0)

        if is_print:
            self.console.print(f"{toml_path} 경로의 파일을 출력하겠습니다.")
            with toml_path.open("rt", encoding="utf-8") as f:
                print(f.read())

            raise Exit(code=0)

        if is_test:
            if not toml_path.exists():
                raise BadParameter(f"{toml_path} 경로에 파일이 없습니다.")

            self.console.print(f"{toml_path} 경로의 파일을 확인하겠습니다.")

            toml_settings = self.load_toml(toml_path=toml_path)
            if not toml_settings:
                raise BadParameter(f"{toml_path} 파일을 읽을 수 없습니다.")

            if len(toml_settings.env) == 0:
                self.console.print(
                    "[red]경고: 등록된 환경변수가 없습니다. (tip: env 항목으로 환경변수를 등록합니다.)[/red]"
                )
            else:
                self.console.print(f"INFO: 등록된 환경변수 = {', '.join(toml_settings.env.keys())}")

                if "UPSTAGE_API_KEY" not in toml_settings.env:
                    self.console.print("ERROR: UPSTAGE_API_KEY 환경변수를 등록해주세요.")

            image_descriptor = ImageDescriptor()

            errors = []
            if "image" not in image_descriptor.system_prompts:
                errors.append("ERROR: [prompt_templates.describe_image] 의 system 항목이 누락되었습니다.")

            if "image" not in image_descriptor.user_prompts:
                errors.append("ERROR: [prompt_templates.describe_image] 의 user 항목이 누락되었습니다.")

            if "table" not in image_descriptor.system_prompts:
                errors.append("ERROR: [prompt_templates.describe_table] 의 system 항목이 누락되었습니다.")

            if "table" not in image_descriptor.user_prompts:
                errors.append("ERROR: [prompt_templates.describe_table] 의 user 항목이 누락되었습니다.")

            if not errors:
                self.console.print(
                    "[green]INFO: image/table에 대한 시스템/유저 프롬프트 템플릿이 모두 등록되어있습니다.[/green]"
                )
            else:
                self.console.print(f"[red]{'\n'.join(errors)}[/red]")

            raise Exit(code=0)

        if is_open:
            if not toml_path.exists():
                raise BadParameter(f"{toml_path} 경로에 파일이 없습니다.")

            self.console.print(f"{toml_path} 경로의 파일을 열겠습니다.")

            try:
                self.open_with_default_editor(toml_path)
            except BadParameter as e:
                self.console.print(f"[red]{str(e)}[/red]")
                raise Exit(code=1)

            raise Exit(code=0)

        self.print_help("pyhub_toml", "")

    def _get_toml_str(self) -> str:
        return f'''
[env]
# UPSTAGE_API_KEY = "up_xxxxx..."
# OPENAI_API_KEY = "sk-xxxxx..."
# ANTHROPIC_API_KEY = "sk-ant-xxxxx..."
# GOOGLE_API_KEY = "AIxxxxx...."

# 무료 PostgreSQL 서비스로서 supabase를 추천합니다. - https://supabase.com
# DATABASE_URL = "postgresql://postgres:pw@localhost:5432/postgres

USER_DEFAULT_TIME_ZONE = "Asia/Seoul"

[prompt_templates.describe_image]
system = """{self._get_template_code("prompts/describe/image/system.md")}"""

user = """{self._get_template_code("prompts/describe/image/user.md")}"""

[prompt_templates.describe_table]
system = """{self._get_template_code("prompts/describe/table/system.md")}"""

user = """{self._get_template_code("prompts/describe/table/user.md")}"""
        '''

    @classmethod
    def _get_template_code(cls, template_name: str) -> str:
        t = get_template(template_name)
        return t.template.source

    @classmethod
    def get_editor_commands(cls) -> list[str]:
        """시스템에서 사용 가능한 에디터 명령어 목록을 반환합니다."""
        # 환경 변수에서 기본 에디터 확인
        editors = []

        # VISUAL or EDITOR 환경 변수 확인
        if "VISUAL" in os.environ:
            editors.append(os.environ["VISUAL"])
        if "EDITOR" in os.environ:
            editors.append(os.environ["EDITOR"])

        if sys.platform.startswith("win"):
            editors.extend(["code", "notepad++", "notepad"])
        else:
            editors.extend(["code", "vim", "nano", "emacs", "gedit"])

        return editors

    def open_with_default_editor(self, file_path: Path) -> None:
        """다양한 에디터 명령을 시도하여 파일을 엽니다."""
        file_path_str = str(file_path)

        # 1. 플랫폼 기본 명령 시도
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["start", file_path_str], shell=True, check=True)
                self.console.print("[green]Windows 기본 프로그램으로 파일을 열었습니다.[/green]")
                return
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", file_path_str], check=True)
                self.console.print("[green]macOS 기본 프로그램으로 파일을 열었습니다.[/green]")
                return
            else:
                subprocess.run(["xdg-open", file_path_str], check=True)
                self.console.print("[green]Linux 기본 프로그램으로 파일을 열었습니다.[/green]")
                return
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # 2. 다양한 에디터 명령 시도
        editors = self.get_editor_commands()
        last_error = None

        for editor in editors:
            try:
                if editor == "code":  # VS Code의 경우 특별 처리
                    subprocess.run(["code", "--wait", file_path_str], check=True)
                    self.console.print("[green]Visual Studio Code로 파일을 열었습니다.[/green]")
                else:
                    subprocess.run([editor, file_path_str], check=True)
                    self.console.print(f"[green]{editor} 에디터로 파일을 열었습니다.[/green]")
                return  # 성공적으로 실행되면 함수 종료
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                last_error = e
                continue

        # 모든 시도가 실패한 경우
        error_msg = f"파일을 열 수 있는 에디터를 찾을 수 없습니다. 시도한 에디터: {', '.join(editors)}"
        if last_error:
            error_msg += f"\n마지막 오류: {str(last_error)}"
        raise BadParameter(error_msg)