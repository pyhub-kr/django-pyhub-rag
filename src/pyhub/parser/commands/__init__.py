import logging
import os
from pathlib import Path
from shutil import rmtree
from typing import Optional, cast

import typer
from django.core.exceptions import ValidationError
from django.core.files import File
from rich.console import Console
from rich.table import Table

from pyhub.logger import LogCapture
from pyhub.parser.json import json_dumps
from pyhub.parser.upstage import UpstageDocumentParseParser
from pyhub.parser.upstage.settings import (
    CACHE_DIR_PATH,
    DEFAULT_BATCH_PAGE_SIZE,
    MAX_BATCH_PAGE_SIZE,
    MAX_CACHE_SIZE_MB,
    SUPPORTED_FILE_EXTENSIONS,
)
from pyhub.parser.upstage.types import (
    CategoryEnum,
    DocumentFormatEnum,
    DocumentSplitStrategyEnum,
    ElementCategoryType,
    OCRModeEnum,
)
from pyhub.parser.utils import manage_cache_directory

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """PyHub RAG CLI tool"""
    if ctx.invoked_subcommand is None:
        console.print(
            """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██████╗  █████╗ ██████╗ ███████╗███████╗██████╗ 
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██████╔╝███████║██████╔╝███████╗█████╗  ██████╔╝
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██╔═══╝ ██╔══██║██╔══██╗╚════██║██╔══╝  ██╔══██╗
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ██║     ██║  ██║██║  ██║███████║███████╗██║  ██║
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
        """,
            style="bold blue",
        )
        console.print("Welcome to PyHub Parser CLI!", style="green")


@app.command()
def upstage(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        help=f"입력 파일 경로 (지원 포맷: {', '.join(SUPPORTED_FILE_EXTENSIONS)})",
    ),
    output_dir_path: Optional[Path] = typer.Option(
        "output",
        "--output-dir-path",
        "-o",
        writable=True,
        help="출력 파일 경로",
    ),
    document_split_strategy: DocumentSplitStrategyEnum = typer.Option(
        DocumentSplitStrategyEnum.PAGE,
        "--document-split-strategy",
        "-s",
        help="문서 분할 전략 | (1) page: 페이지 단위로 Document 생성, (2) element: Element 단위로 Document 생성, (3) none: 파일 전체를 하나의 Document로 생성",
    ),
    ocr_mode: OCRModeEnum = typer.Option(OCRModeEnum.FORCE, help="OCR 모드"),
    document_format: DocumentFormatEnum = typer.Option(DocumentFormatEnum.MARKDOWN, help="생성할 문서 포맷"),
    base64_encodings: str = typer.Option(
        "figure,chart,table",
        help=f"Base64로 인코딩할 요소 카테고리 목록 (쉼표로 구분): {', '.join([e.value for e in CategoryEnum])}",
        callback=lambda x: validate_categories(x),
    ),
    ignore_element_category: str = typer.Option(
        "header,footer",
        "--ignore",
        help="파싱 결과에서 제외할 요소 카테고리 목록 (쉼표로 구분). 기본값으로 header와 footer가 제외됩니다.",
        callback=lambda x: validate_categories(x),
    ),
    batch_page_size: int = typer.Option(
        DEFAULT_BATCH_PAGE_SIZE,
        "--batch-page-size",
        "-b",
        min=1,
        max=MAX_BATCH_PAGE_SIZE,
        help=(
            f"한 번의 API 호출에서 처리할 PDF 페이지 수입니다. Upstage Document Parse API는 "
            f"하나의 API 호출당 최대 {MAX_BATCH_PAGE_SIZE}페이지까지 지원합니다. "
            f"{MAX_BATCH_PAGE_SIZE}페이지를 초과하는 PDF 파일에는 이 설정이 꼭 필요합니다."
        ),
    ),
    max_page: int = typer.Option(0, "--max-page", "-m", min=0, help="처리할 최대 페이지 수 (0: 모든 페이지)"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v", help="상세한 처리 정보 표시"),
    is_force: bool = typer.Option(False, "--force", "-f", help="확인 없이 출력 폴더 삭제 후 재생성"),
    upstage_api_key: Optional[str] = typer.Option(
        None, help="Upstage API Key. 지정하지 않으면 UPSTAGE_API_KEY 환경 변수 사용"
    ),
    is_unified_output: bool = typer.Option(False, "--unified-file", "-u", help="통합 파일 생성 여부"),
    is_cache_clear: bool = typer.Option(
        False, "--clear-cache", help="API 응답 캐시를 초기화합니다. 이전에 저장된 API 응답을 무시하고 새로 요청합니다."
    ),
):
    if upstage_api_key is None:
        upstage_api_key = os.environ.get("UPSTAGE_API_KEY")

    if not upstage_api_key:
        raise typer.BadParameter(
            "--upstage-api-key 옵션이나 UPSTAGE_API_KEY 환경 변수를 통해 Upstage API Key를 설정해주세요."
        )

    base64_encoding_category_list = cast(list[ElementCategoryType], base64_encodings)
    ignore_element_category_list = cast(list[ElementCategoryType], ignore_element_category)

    # Check if output file exists and confirm overwrite if force option is not set
    if output_dir_path.exists():
        if is_force:
            if is_verbose:
                console.print(f"[yellow]출력 폴더 {output_dir_path}을 삭제합니다.[/yellow]")
            rmtree(output_dir_path, ignore_errors=True)
        else:
            overwrite = typer.confirm(
                f"출력 폴더 {output_dir_path}이(가) 이미 존재합니다. 삭제 후에 재생성하시겠습니까?"
            )
            if overwrite:
                if is_verbose:
                    console.print(f"[yellow]출력 폴더 {output_dir_path}을(를) 삭제합니다.[/yellow]")
                rmtree(output_dir_path, ignore_errors=True)
            else:
                console.print("[yellow]작업이 취소되었습니다.[/yellow]")
                raise typer.Exit(code=0)

    output_dir_path.mkdir(parents=True, exist_ok=True)

    # create one based on input_path with .jsonl extension
    jsonl_output_path = output_dir_path / input_path.with_suffix(".jsonl")

    if is_unified_output:
        ext = DocumentFormatEnum.to_ext(document_format)
        unified_output_path = output_dir_path / input_path.with_suffix(ext).name
        unified_output_path.unlink(missing_ok=True)
    else:
        unified_output_path = None

    # Debug: Print all arguments except api_key
    if is_verbose:
        # Check if input file is a PDF
        is_pdf = input_path.suffix.lower() == ".pdf"

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("매개변수", style="cyan")
        table.add_column("값", style="green")

        # Add rows to the table
        table.add_row("입력 문서 파일 경로", str(input_path.absolute()))
        table.add_row("파일 생성 폴더", str(output_dir_path.absolute()))
        table.add_row("Document 분할 전략", document_split_strategy.value)
        table.add_row("OCR 모드", ocr_mode.value)
        table.add_row("생성할 Document 포맷", document_format.value)
        table.add_row("Base64 인코딩", ", ".join(base64_encoding_category_list))
        table.add_row("제외할 요소", ", ".join(ignore_element_category_list))
        table.add_row("통합 문서 생성 여부", str(is_unified_output))

        # Add batch size with warning if needed
        batch_size_str = str(batch_page_size)
        if not is_pdf and batch_page_size == DEFAULT_BATCH_PAGE_SIZE:
            batch_size_str += " [yellow](경고: PDF 파일에서만 사용됩니다.)[/yellow]"
        table.add_row("배치 크기", batch_size_str)

        table.add_row("최대 페이지", str(max_page))
        table.add_row("상세 정보", str(is_verbose))
        table.add_row("강제 덮어쓰기", str(is_force))

        # Print the table
        console.print(table)

    # Check if input file is a PDF. Warn if batch_size is specified but file is not a PDF
    is_pdf = input_path.suffix.lower() == ".pdf"
    if not is_pdf and batch_page_size != DEFAULT_BATCH_PAGE_SIZE and not is_verbose:
        console.print(f"[yellow]경고: 배치 크기 매개변수({batch_page_size})는 PDF가 아닌 파일에는 무시됩니다.[/yellow]")

    parser = UpstageDocumentParseParser(
        upstage_api_key=upstage_api_key,
        split=document_split_strategy.value,
        max_page=max_page,
        ocr_mode=ocr_mode.value,
        document_format=document_format.value,
        base64_encoding_category_list=base64_encoding_category_list,
        ignore_element_category_list=ignore_element_category_list,
        verbose=is_verbose,
    )

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    with LogCapture(console=console, level=log_level):
        try:
            if is_cache_clear and CACHE_DIR_PATH.exists():
                if is_verbose:
                    console.print(f"[yellow]캐시 폴더 삭제 : {CACHE_DIR_PATH}[/yellow]")
                rmtree(CACHE_DIR_PATH, ignore_errors=True)

            CACHE_DIR_PATH.mkdir(exist_ok=True)
            manage_cache_directory(CACHE_DIR_PATH, MAX_CACHE_SIZE_MB)

            with input_path.open("rb") as file:
                django_file = File(file)
                parser.is_valid(django_file, raise_exception=True)

                with jsonl_output_path.open("wt", encoding="utf-8") as f:
                    document_count = 0
                    for document in parser.lazy_parse_sync(
                        django_file,
                        batch_page_size=batch_page_size,
                        ignore_validation=True,
                    ):
                        f.write(json_dumps(document) + "\n")

                        if unified_output_path is not None:
                            with unified_output_path.open("at") as uf:
                                if document_count > 0:
                                    uf.write("\n\n")
                                uf.write(document.page_content)

                            for name, _file in document.files.items():
                                output_path = output_dir_path / name
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                output_path.open("wb").write(_file.read())

                        document_count += 1

                    console.print(
                        f"[green]성공:[/green] {jsonl_output_path} 경로에 {document_count}개의 Document를 jsonl 포맷으로 생성했습니다."
                    )
        except FileNotFoundError:
            console.print(f"[bold red]오류:[/bold red] 파일을 찾을 수 없습니다: {input_path}")
            raise typer.Exit(code=1)
        except PermissionError:
            console.print(f"[bold red]오류:[/bold red] 파일 접근 권한이 거부되었습니다: {input_path}")
            raise typer.Exit(code=1)
        except ValidationError as e:
            console.print("[bold red]유효성 검사 오류:[/bold red] 파일이 필요한 제약 조건을 충족하지 않습니다")
            console.print(f"[red]세부 정보: {str(e)}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red]오류:[/bold red] 파일을 열거나 처리하는 데 실패했습니다: {input_path}")
            console.print(f"[red]세부 정보: {str(e)}[/red]")

            import traceback

            print(traceback.format_exc())

            raise typer.Exit(code=1)


def validate_categories(categories_str: str) -> list[str]:
    """Raises BadParameter exception if values not in CategoryEnum are entered."""
    if not categories_str:
        return []

    invalid_categories = []
    valid_categories = []

    for item in categories_str.split(","):
        category = item.strip()
        if category in CategoryEnum:
            valid_categories.append(category)
        else:
            invalid_categories.append(category)

    if invalid_categories:
        valid_values = [e.value for e in CategoryEnum]
        raise typer.BadParameter(
            f"유효하지 않은 값: {', '.join(invalid_categories)}. 유효한 값: {', '.join(valid_values)}"
        )

    return valid_categories
