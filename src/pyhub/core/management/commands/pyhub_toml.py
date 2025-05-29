import os
from pathlib import Path
from typing import Annotated, Optional

from django.template.loader import get_template
from django_rich.management import RichCommand
from django_typer.management import TyperCommand
from typer import Option, BadParameter, Exit, Argument

from pyhub import load_toml
from pyhub.config import DEFAULT_TOML_PATH
from pyhub.parser.upstage.parser import ImageDescriptor
from pyhub.core.toml_utils import get_default_toml_content, open_file_with_editor


class Command(RichCommand, TyperCommand):
    def handle(
        self,
        toml_path: Annotated[Path, Argument(help="toml 파일 경로")] = DEFAULT_TOML_PATH,
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
        is_edit: Annotated[
            bool, Option("--edit", "-e", help="지정 경로의 toml 파일을 디폴트 편집기로 편집합니다.")
        ] = False,
    ):
        if toml_path.suffix != ".toml":
            self.console.print(f"[red]오류: 파일 확장자는 .toml이어야 합니다.[/red]")
            self.console.print(f"[dim]입력된 파일: {toml_path}[/dim]")
            raise Exit(code=1)

        if is_create or is_force_create:
            if toml_path.exists():
                if is_force_create:
                    self.console.print(f"[yellow]경고: {toml_path} 파일을 덮어쓰기 합니다.[/yellow]")
                else:
                    self.console.print(f"[red]오류: {toml_path} 파일이 이미 존재합니다.[/red]")
                    self.console.print(f"[dim]다음 중 하나를 선택하세요:[/dim]")
                    self.console.print(f"  • 기존 파일을 덮어쓰려면: [cyan]pyhub toml create --force[/cyan]")
                    self.console.print(f"  • 기존 파일을 편집하려면: [cyan]pyhub toml edit[/cyan]")
                    self.console.print(f"  • 기존 파일을 확인하려면: [cyan]pyhub toml show[/cyan]")
                    raise Exit(code=1)

            try:
                # 디렉토리가 없으면 생성
                toml_path.parent.mkdir(parents=True, exist_ok=True)
                with toml_path.open("wt", encoding="utf-8") as f:
                    f.write(self._get_toml_str())
            except PermissionError:
                self.console.print(f"[red]오류: 파일을 생성할 권한이 없습니다.[/red]")
                self.console.print(f"[dim]경로: {toml_path}[/dim]")
                raise Exit(code=1)
            except OSError as e:
                self.console.print(f"[red]오류: 파일을 생성할 수 없습니다.[/red]")
                self.console.print(f"[dim]상세: {e}[/dim]")
                raise Exit(code=1)
            else:
                self.console.print(f"[green]✓ 설정 파일이 생성되었습니다: {toml_path}[/green]")
                self.console.print(f"[dim]다음 명령으로 파일을 편집할 수 있습니다:[/dim]")
                self.console.print(f"  [cyan]pyhub toml edit[/cyan]")

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

            toml_settings = load_toml(toml_path=toml_path)
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

        if is_edit:
            if not toml_path.exists():
                raise BadParameter(f"{toml_path} 경로에 파일이 없습니다.")

            self.console.print(f"{toml_path} 경로의 파일을 편집합니다.")

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


    def open_with_default_editor(self, file_path: Path) -> None:
        """공통 함수를 사용하여 파일을 편집기로 엽니다."""
        if not open_file_with_editor(file_path):
            raise BadParameter("파일을 열 수 있는 에디터를 찾을 수 없습니다.")
