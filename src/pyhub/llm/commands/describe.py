import logging
from pathlib import Path
from typing import Optional, Union

import typer
from django.core.files import File
from PIL import Image as PILImage
from rich.console import Console
from rich.table import Table

from pyhub import init
from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum

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
    ctx: typer.Context,
    image_paths: Optional[list[Path]] = typer.Argument(
        None,
        help="설명을 요청할 이미지 파일 경로 (여러 개 가능)",
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
        help="toml 내 prompt_templates 프롬프트 타입. (디폴트: describe_image)",
    ),
    temperature: float = typer.Option(0.2, help="LLM 응답의 온도 설정 (0.0-2.0, 높을수록 다양한 응답)"),
    max_tokens: int = typer.Option(1000, help="응답의 최대 토큰 수"),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="출력 형식 (text, json, markdown)",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="결과를 저장할 파일 경로",
    ),
    batch_output_dir: Optional[Path] = typer.Option(
        None,
        "--batch-output-dir",
        help="배치 처리 시 결과를 저장할 디렉토리",
    ),
    show_stats: bool = typer.Option(
        False,
        "--stats",
        help="토큰 사용량 통계 표시",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """LLM에게 이미지 설명을 요청합니다."""

    # 이미지 경로가 제공되지 않은 경우 help 출력
    if not image_paths:
        console.print(ctx.get_help())
        raise typer.Exit()

    # 모든 이미지 파일 유효성 검사
    valid_image_paths = []
    for image_path in image_paths:
        try:
            valid_path = validate_image_file(image_path)
            valid_image_paths.append(valid_path)
        except typer.BadParameter as e:
            console.print(f"[red]오류: {e}[/red]")
            continue

    if not valid_image_paths:
        console.print("[red]처리할 수 있는 유효한 이미지 파일이 없습니다.[/red]")
        raise typer.Exit(1)

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    # LLM 명령 시에 PyPDF2 라이브러리 의존성이 걸리지 않도록 임포트 위치 조정
    from pyhub.parser.upstage.parser import ImageDescriptor

    if prompt_type is None:
        prompt_templates = ImageDescriptor.get_prompts("describe_image")
    else:
        toml_path = Path.home() / ".pyhub.toml"
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

    # 배치 출력 디렉토리 생성
    if batch_output_dir and len(valid_image_paths) > 1:
        batch_output_dir.mkdir(parents=True, exist_ok=True)

    # LLM 생성
    llm = LLM.create(
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # 전체 통계
    total_usage = None
    results = []

    import time

    from pyhub.llm.types import Usage

    # 각 이미지 처리
    for idx, image_path in enumerate(valid_image_paths, 1):
        if len(valid_image_paths) > 1:
            console.print(f"\n[bold blue]처리 중 ({idx}/{len(valid_image_paths)}): {image_path.name}[/bold blue]")

        start_time = time.time()

        try:
            with image_path.open("rb") as image_file:
                files = [File(file=image_file)]

                # 응답 받기
                response_text = ""
                usage = None

                for chunk in llm.ask(query, files=files, stream=True, enable_cache=enable_cache):
                    response_text += chunk.text
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage = chunk.usage

                    # 단일 파일 처리 시에만 실시간 출력
                    if len(valid_image_paths) == 1:
                        console.print(chunk.text, end="")

                elapsed_time = time.time() - start_time

                # 결과 저장
                result = {
                    "image": str(image_path),
                    "description": response_text,
                    "model": model.value,
                    "elapsed_time": elapsed_time,
                }

                if usage:
                    result["usage"] = {
                        "input_tokens": usage.input,
                        "output_tokens": usage.output,
                        "total_tokens": usage.total,
                    }
                    # 전체 통계 업데이트
                    if total_usage is None:
                        total_usage = Usage()
                    total_usage += usage

                results.append(result)

                # 배치 출력 시 개별 파일 저장
                if batch_output_dir and len(valid_image_paths) > 1:
                    output_file = batch_output_dir / f"{image_path.stem}_description.{output_format}"
                    save_result(output_file, result, output_format)
                    if is_verbose:
                        console.print(f"[dim]저장됨: {output_file}[/dim]")

                # 배치 처리 시 간단한 결과 표시
                if len(valid_image_paths) > 1:
                    if output_format == "text":
                        console.print(response_text[:200] + "..." if len(response_text) > 200 else response_text)
                    else:
                        console.print(f"[green]✓ 완료 ({elapsed_time:.2f}초)[/green]")

        except Exception as e:
            console.print(f"[red]오류 처리 중 {image_path}: {e}[/red]")
            continue

    # 단일 파일 처리 시 줄바꿈
    if len(valid_image_paths) == 1:
        console.print()

    # 전체 결과 저장
    if output_path:
        if len(valid_image_paths) == 1:
            save_result(output_path, results[0], output_format)
        else:
            # 배치 처리 결과는 항상 JSON으로 저장
            save_result(output_path, results, "json")
        console.print(f"[green]결과가 저장되었습니다: {output_path}[/green]")

    # 통계 표시
    if show_stats and total_usage:
        stats_table = Table(title="전체 통계")
        stats_table.add_column("항목", style="cyan")
        stats_table.add_column("값", style="green")
        stats_table.add_row("처리된 이미지", str(len(results)))
        stats_table.add_row("총 입력 토큰", str(total_usage.input))
        stats_table.add_row("총 출력 토큰", str(total_usage.output))
        stats_table.add_row("총 토큰", str(total_usage.total))
        console.print(stats_table)


def save_result(output_path: Path, result: Union[dict, list], format: str):
    """결과를 지정된 형식으로 저장"""
    import json

    if format == "json":
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    elif format == "markdown":
        with output_path.open("w", encoding="utf-8") as f:
            if isinstance(result, list):
                # 배치 결과
                for item in result:
                    f.write(f"## {Path(item['image']).name}\n\n")
                    f.write(f"{item['description']}\n\n")
                    f.write("---\n\n")
            else:
                # 단일 결과
                f.write(f"# {Path(result['image']).name}\n\n")
                f.write(f"{result['description']}\n")
    else:  # text
        with output_path.open("w", encoding="utf-8") as f:
            if isinstance(result, list):
                # 배치 결과
                for item in result:
                    f.write(f"=== {Path(item['image']).name} ===\n\n")
                    f.write(f"{item['description']}\n\n")
            else:
                # 단일 결과
                f.write(result["description"])
