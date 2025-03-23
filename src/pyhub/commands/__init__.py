from pathlib import Path
from typing import Optional

import typer
from django.template.loader import get_template
from rich.console import Console

from pyhub import init, load_toml, print_for_main
from pyhub.parser.upstage.parser import ImageDescriptor

app = typer.Typer()
console = Console()


app.callback(invoke_without_command=True)(print_for_main)


@app.command()
def toml(
    ctx: typer.Context,
    toml_path: Optional[Path] = typer.Argument(
        Path.home() / ".pyhub.toml",
        help="toml 파일 경로",
    ),
    is_create: bool = typer.Option(
        False,
        "--create",
        "-c",
        help="지정 경로에 toml 설정 파일을 생성합니다.",
    ),
    is_print: bool = typer.Option(
        False,
        "--print",
        "-p",
        help="지정 경로의 toml 설정 파일을 출력합니다.",
    ),
    is_test: bool = typer.Option(
        False,
        "--test",
        "-t",
        help="지정 경로에 toml 설정 파일을 검증합니다.",
    ),
):
    if toml_path.suffix != ".toml":
        raise typer.BadParameter("확장자를 .toml로 지정해주세요.")

    toml_path = toml_path.resolve()

    init(debug=True)

    if is_create:
        if toml_path.exists():
            raise typer.BadParameter(f"{toml_path} 경로에 파일이 이미 있습니다.")

        try:
            with toml_path.open("wt", encoding="utf-8") as f:
                f.write(_get_toml_str())
        except Exception as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=1)
        else:
            console.print(f"[green]{toml_path} 경로에 설정 파일 초안을 생성했습니다. 목적에 맞게 수정해주세요.[/green]")
    elif is_print:
        with toml_path.open("rt", encoding="utf-8") as f:
            print(f.read())
    elif is_test:
        if not toml_path.exists():
            raise typer.BadParameter(f"{toml_path} 경로에 파일이 없습니다.")

        console.print(f"{toml_path} 경로의 파일을 읽습니다.")

        toml_settings = load_toml(toml_path=toml_path)
        if not toml_settings:
            raise typer.BadParameter(f"{toml_path} 파일을 읽을 수 없습니다.")

        if len(toml_settings.env) == 0:
            console.print("[red]경고: 등록된 환경변수가 없습니다. (tip: env 항목으로 환경변수를 등록합니다.)[/red]")
        else:
            console.print(f"INFO: 등록된 환경변수 = {', '.join(toml_settings.env.keys())}")

            if "UPSTAGE_API_KEY" not in toml_settings.env:
                console.print("ERROR: UPSTAGE_API_KEY 환경변수를 등록해주세요.")

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
            console.print(
                "[green]INFO: image/table에 대한 시스템/유저 프롬프트 템플릿이 모두 등록되어있습니다.[/green]"
            )
        else:
            console.print(f"[red]{'\n'.join(errors)}[/red]")

    else:
        console.print(ctx.get_help())


def _get_toml_str() -> str:
    return f'''
[env]
# UPSTAGE_API_KEY = "up_xxxxx..."
# OPENAI_API_KEY = "sk-xxxxx..."
# ANTHROPIC_API_KEY = "sk-ant-xxxxx..."
# GOOGLE_API_KEY = "AIxxxxx...."

[prompt_templates.describe_image]
system = """{_get_template_code("prompts/describe/image/system.md")}"""

user = """{_get_template_code("prompts/describe/image/user.md")}"""

[prompt_templates.describe_table]
system = """{_get_template_code("prompts/describe/table/system.md")}"""

user = """{_get_template_code("prompts/describe/table/user.md")}"""
    '''


def _get_template_code(template_name: str) -> str:
    t = get_template(template_name)
    return t.template.source
