import logging
from pathlib import Path
from typing import Optional

import typer
from django.core.files import File
from PIL import Image as PILImage
from rich.console import Console
from rich.table import Table

from pyhub import get_version, init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum, LLMVendorEnum
from pyhub.parser.upstage.parser import ImageDescriptor

console = Console()


def validate_image_file(image_path: Path) -> Path:
    """이미지 파일 유효성을 검사합니다."""
    # 파일 존재 여부 확인
    if not image_path.exists():
        raise typer.BadParameter(f"파일이 존재하지 않습니다: {image_path}")

    # PIL로 이미지 파일 검증
    try:
        with PILImage.open(image_path) as img:
            img.verify()  # 이미지 파일 검증
        return image_path
    except Exception as e:
        raise typer.BadParameter(f"유효하지 않은 이미지 파일입니다: {str(e)}")


def describe(
    image_path: Path = typer.Argument(
        ...,
        help="설명을 요청할 이미지 파일 경로",
        callback=validate_image_file,  # 콜백 함수 추가
    ),
    vendor: LLMVendorEnum = typer.Option(
        LLMVendorEnum.OPENAI,
        "--vendor",
        "-v",
        help="LLM 벤더",
    ),
    model: LLMChatModelEnum = typer.Option(
        LLMChatModelEnum.GPT_4O_MINI,
        "--model",
        "-m",
        help="LLM Chat 모델. LLM 벤더에 맞게 지정해주세요.",
    ),
    prompt_type: Optional[str] = typer.Option(
        None,
        "--prompt-type",
        help="~/.pyhub.toml 에서 prompt_templates 내의 프롬프트 타입. (디폴트: describe_image)",
    ),
    temperature: float = typer.Option(0.2, help="LLM 응답의 온도 설정 (0.0-2.0, 높을수록 다양한 응답)"),
    max_tokens: int = typer.Option(1000, help="응답의 최대 토큰 수"),
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
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    is_print_version: bool = typer.Option(False, "--version", help="현재 패키지 버전 출력"),
):
    """LLM에게 이미지 설명을 요청합니다."""

    if is_print_version:
        console.print(get_version())
        raise typer.Exit()

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    if prompt_type is None:
        prompt_templates = ImageDescriptor.get_prompts("describe_image")
    else:
        if not toml_path.exists():
            raise typer.BadParameter(f"{toml_path} 파일을 먼저 생성해주세요. (명령 예: pyhub toml --create)")

        try:
            prompt_templates = ImageDescriptor.get_prompts(prompt_type, use_default_prompts=False)
        except KeyError as e:
            raise typer.BadParameter(
                f"{toml_path}에서 {prompt_type} 프롬프트 타입의 프롬프트를 찾을 수 없습니다."
            ) from e

    system_prompt = prompt_templates["system"]
    query = prompt_templates["user"]

    if is_verbose:
        table = Table()
        table.add_column("설정", style="cyan")
        table.add_column("값", style="green")
        table.add_row("image_path", str(image_path.resolve()))
        table.add_row("vendor", vendor.value)
        table.add_row("model", model.value)
        table.add_row("temperature", str(temperature))
        table.add_row("max_tokens", str(max_tokens))
        table.add_row("system prompt", system_prompt)
        table.add_row("user prompt", query)
        table.add_row("toml_path", f"{toml_path.resolve()} ({"Found" if toml_path.exists() else "Not found"})")
        table.add_row("env_path", f"{env_path.resolve()} ({"Found" if env_path.exists() else "Not found"})")
        console.print(table)

    with image_path.open("rb") as image_file:
        files = [File(file=image_file)]

        llm = LLM.create(
            model=model.value,
            vendor=vendor.value,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        for chunk in llm.ask(query, files=files, stream=True):
            print(chunk.text, end="", flush=True)
        print()
