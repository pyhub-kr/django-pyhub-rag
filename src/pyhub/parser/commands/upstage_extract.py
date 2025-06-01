"""Upstage Information Extract CLI command."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import typer
from django.core.files import File
from rich.console import Console
from rich.table import Table

from pyhub import init
from pyhub.caches import cache_clear_all
from pyhub.config import DEFAULT_ENV_PATH, DEFAULT_TOML_PATH
from pyhub.parser.upstage.extractor import (
    BatchInformationExtractor,
    ExtractionSchema,
    UpstageInformationExtractor,
)

console = Console()


def upstage_extract(
    ctx: typer.Context,
    input_path: Optional[Path] = typer.Argument(
        None,
        help="입력 문서 파일 경로 (PDF, 이미지 등)",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="추출 결과를 저장할 파일 경로 (기본: 입력파일명.extracted.json)",
    ),
    schema_path: Optional[Path] = typer.Option(
        None,
        "--schema",
        "-s",
        help="추출 스키마 JSON 파일 경로",
    ),
    keys: Optional[str] = typer.Option(
        None,
        "--keys",
        "-k",
        help="추출할 키 목록 (쉼표로 구분, 예: invoice_date,total_amount,vendor_name)",
    ),
    extraction_type: str = typer.Option(
        "universal",
        "--type",
        "-t",
        help="추출 타입 (universal: 범용 추출, prebuilt: 사전 학습 모델)",
    ),
    document_type: Optional[str] = typer.Option(
        None,
        "--document-type",
        "-d",
        help="문서 타입 (prebuilt 모드에서 필수, 예: invoice, receipt, contract)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="출력 포맷 (json, jsonl, csv)",
    ),
    batch_dir: Optional[Path] = typer.Option(
        None,
        "--batch-dir",
        "-b",
        help="배치 처리할 디렉토리 경로 (개별 파일 대신 디렉토리 내 모든 문서 처리)",
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--no-pretty",
        help="JSON 출력을 보기 좋게 포맷팅",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 로그 출력"),
    is_ignore_cache: bool = typer.Option(
        False,
        "--ignore-cache",
        help="API 응답 캐시를 무시하고 항상 새로운 API 요청",
    ),
    is_cache_clear_all: bool = typer.Option(
        False,
        "--cache-clear-all",
        help="모든 캐시를 초기화",
    ),
    upstage_api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="Upstage API Key (미지정시 UPSTAGE_API_KEY 환경변수 사용)",
    ),
    toml_path: Optional[Path] = typer.Option(
        DEFAULT_TOML_PATH,
        "--toml-file",
        help="toml 설정 파일 경로",
    ),
    env_path: Optional[Path] = typer.Option(
        DEFAULT_ENV_PATH,
        "--env-file",
        help="환경 변수 파일(.env) 경로",
    ),
    is_debug: bool = typer.Option(False, "--debug", help="디버그 모드"),
):
    """Upstage Information Extract API를 사용하여 문서에서 구조화된 정보를 추출합니다."""

    # Check if input is provided
    if not input_path and not batch_dir:
        console.print(ctx.get_help())
        raise typer.Exit()

    if input_path and batch_dir:
        console.print("[red]오류: --batch-dir와 input_path를 동시에 지정할 수 없습니다.[/red]")
        raise typer.Exit(1)

    # Initialize Django
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=is_debug, log_level=log_level, toml_path=toml_path, env_path=env_path)

    # Get API key
    if upstage_api_key is None:
        upstage_api_key = os.environ.get("UPSTAGE_API_KEY")

    if not upstage_api_key:
        console.print("[red]오류: --api-key 옵션이나 UPSTAGE_API_KEY 환경 변수를 설정해주세요.[/red]")
        raise typer.Exit(1)

    # Validate API key format
    if not upstage_api_key.startswith("up_"):
        console.print("[red]오류: Upstage API Key 형식이 올바르지 않습니다. 'up_'로 시작해야 합니다.[/red]")
        raise typer.Exit(1)

    # Clear cache if requested
    if is_cache_clear_all:
        cache_clear_all()
        console.print("[green]캐시를 모두 초기화했습니다.[/green]")

    # Prepare schema
    schema = None
    if schema_path:
        try:
            schema = ExtractionSchema.from_json_file(schema_path)
            if is_verbose:
                console.print(f"[blue]스키마 로드: {schema_path}[/blue]")
        except Exception as e:
            console.print(f"[red]스키마 파일 로드 실패: {e}[/red]")
            raise typer.Exit(1)

    # Parse keys
    key_list = None
    if keys:
        key_list = [k.strip() for k in keys.split(",") if k.strip()]
        if is_verbose:
            console.print(f"[blue]추출 키: {', '.join(key_list)}[/blue]")

    # Validate extraction parameters
    if extraction_type == "universal" and not (schema or key_list):
        console.print("[red]오류: universal 추출 모드에서는 --schema 또는 --keys 옵션이 필요합니다.[/red]")
        raise typer.Exit(1)

    if extraction_type == "prebuilt" and not document_type:
        console.print("[red]오류: prebuilt 추출 모드에서는 --document-type 옵션이 필요합니다.[/red]")
        raise typer.Exit(1)

    # Print configuration if verbose
    if is_verbose:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("설정", style="cyan")
        table.add_column("값", style="green")

        if input_path:
            table.add_row("입력 파일", str(input_path))
        else:
            table.add_row("배치 디렉토리", str(batch_dir))

        table.add_row("추출 타입", extraction_type)
        if document_type:
            table.add_row("문서 타입", document_type)
        if schema_path:
            table.add_row("스키마 파일", str(schema_path))
        if key_list:
            table.add_row("추출 키", ", ".join(key_list))
        table.add_row("출력 포맷", output_format)

        console.print(table)

    # Create extractor
    extractor_class = BatchInformationExtractor if batch_dir else UpstageInformationExtractor
    extractor = extractor_class(
        api_key=upstage_api_key,
        extraction_type=extraction_type,
        ignore_cache=is_ignore_cache,
        verbose=is_verbose,
    )

    try:
        # Process single file or batch
        if input_path:
            # Single file processing
            with input_path.open("rb") as f:
                django_file = File(f, name=input_path.name)

                console.print(f"[yellow]추출 중: {input_path.name}[/yellow]")
                result = extractor.extract_sync(
                    django_file,
                    schema=schema,
                    keys=key_list,
                    document_type=document_type,
                )

                # Determine output path
                if not output_path:
                    output_path = input_path.with_suffix(".extracted.json")

                # Save result
                save_extraction_result(result, output_path, output_format, pretty)
                console.print(f"[green]추출 완료: {output_path}[/green]")

                # Display result summary
                if is_verbose:
                    display_extraction_summary(result)

        else:
            # Batch processing
            files_to_process = []
            for file_path in batch_dir.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in [
                    ".pdf",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".bmp",
                    ".tiff",
                ]:
                    files_to_process.append(file_path)

            if not files_to_process:
                console.print(f"[yellow]경고: {batch_dir}에 처리할 문서가 없습니다.[/yellow]")
                raise typer.Exit(0)

            console.print(f"[yellow]{len(files_to_process)}개 문서 배치 처리 시작[/yellow]")

            # Process all files
            django_files = []
            for file_path in files_to_process:
                with file_path.open("rb") as f:
                    django_files.append(File(f, name=file_path.name))

            import asyncio

            results = asyncio.run(
                extractor.extract_batch(
                    django_files,
                    schema=schema,
                    keys=key_list,
                    document_type=document_type,
                )
            )

            # Save batch results
            output_dir = batch_dir / "extracted"
            output_dir.mkdir(exist_ok=True)

            for i, (file_path, result) in enumerate(zip(files_to_process, results)):
                output_path = output_dir / file_path.with_suffix(".extracted.json").name
                save_extraction_result(result, output_path, output_format, pretty)

            console.print(f"[green]배치 처리 완료: {len(results)}개 문서[/green]")
            console.print(f"[green]결과 저장 위치: {output_dir}[/green]")

    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")
        if is_debug:
            console.print_exception()
        raise typer.Exit(1)


def save_extraction_result(data: dict, output_path: Path, format: str = "json", pretty: bool = True):
    """Save extraction result to file."""
    if format == "json":
        with output_path.open("w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)

    elif format == "jsonl":
        with output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    elif format == "csv":
        # Simple CSV output for flat data
        import csv

        with output_path.open("w", encoding="utf-8", newline="") as f:
            if data and not isinstance(data, dict):
                console.print("[yellow]경고: CSV 형식은 단순 키-값 데이터에만 적합합니다.[/yellow]")
                return

            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)


def display_extraction_summary(data: dict):
    """Display extraction result summary."""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("필드", style="cyan")
    table.add_column("값", style="white")

    def add_items(data_dict, prefix=""):
        for key, value in data_dict.items():
            if isinstance(value, dict):
                add_items(value, f"{prefix}{key}.")
            elif isinstance(value, list):
                table.add_row(f"{prefix}{key}", f"[{len(value)} items]")
            else:
                table.add_row(f"{prefix}{key}", str(value)[:100])

    add_items(data)
    console.print("\n[bold]추출 결과:[/bold]")
    console.print(table)
