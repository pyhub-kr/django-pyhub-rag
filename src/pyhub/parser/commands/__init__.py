import logging
import os
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from typing import List, Optional, Union, cast

import typer
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import URLValidator
from rich.console import Console
from rich.table import Table

from pyhub import get_version, init
from pyhub.llm.types import LanguageEnum, LLMChatModelEnum, LLMVendorEnum
from pyhub.parser.json import json_dumps
from pyhub.parser.upstage import UpstageDocumentParseParser
from pyhub.parser.upstage.parser import ImageDescriptor
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
from pyhub.rag.utils import get_literal_values

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    is_print_version: bool = typer.Option(False, "--version", "-V", help="현재 패키지 버전 출력"),
    is_help: bool = typer.Option(False, "--help", "-h", help="도움말 메시지 출력"),
):
    """PyHub RAG CLI tool"""
    if is_print_version:
        console.print(get_version())
        raise typer.Exit()

    if is_help:
        print_help(ctx)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print(
            """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██████╗  █████╗ ██████╗ ███████╗███████╗██████╗ 
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██████╔╝███████║██████╔╝███████╗█████╗  ██████╔╝
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██╔═══╝ ██╔══██║██╔══██╗╚════██║██╔══╝  ██╔══██╗
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ██║     ██║  ██║██║  ██║███████║███████╗██║  ██║
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
        """
        )

        console.print(f"Welcome to PyHub Parser CLI! {get_version()}")
        console.print(
            "\n장고와 함께 웹 기반의 PDF 지식 저장소를 손쉽게 구축하실 수 있습니다. - 파이썬사랑방 (me@pyhub.kr)",
            style="green",
        )


@app.command()
def upstage(
    input_path: Optional[Path] = typer.Argument(
        None,
        help=f"입력 파일 경로 (지원 포맷: {', '.join(SUPPORTED_FILE_EXTENSIONS)})",
    ),
    output_dir_path: Optional[Path] = typer.Option(
        "output",
        "--output-dir-path",
        "-o",
        writable=True,
        help="Document jsonl 파일을 생성할 폴더 경로",
    ),
    document_format: DocumentFormatEnum = typer.Option(
        DocumentFormatEnum.MARKDOWN,
        "--document-format",
        "-d",
        help="생성할 문서 포맷",
    ),
    is_create_unified_output: bool = typer.Option(
        False,
        "--create-unified-file",
        "-c",
        help="통합 파일 생성 여부",
    ),
    document_split_strategy: DocumentSplitStrategyEnum = typer.Option(
        DocumentSplitStrategyEnum.PAGE,
        "--document-split-strategy",
        "-s",
        help=(
            "문서 분할 전략 | (1) page: 페이지 단위로 Document 생성, (2) element: Element 단위로 Document 생성, "
            "(3) none: 파일 전체를 하나의 Document로 생성"
        ),
    ),
    batch_page_size: int = typer.Option(
        DEFAULT_BATCH_PAGE_SIZE,
        "--batch-page-size",
        "-b",
        min=1,
        max=MAX_BATCH_PAGE_SIZE,
        help=(
            f"한 번의 API 호출에서 처리할 PDF 페이지 수입니다. Upstage Document Parse API는 "
            f"하나의 API 호출당 최대 {MAX_BATCH_PAGE_SIZE} 페이지까지 지원합니다. "
            f"{MAX_BATCH_PAGE_SIZE}페이지를 초과하는 PDF 파일에는 이 설정이 꼭 필요합니다."
        ),
    ),
    max_page: int = typer.Option(
        0,
        "--max-page",
        "-m",
        min=0,
        help="처리할 최대 페이지 수 (0: 모든 페이지)",
    ),
    ocr_mode: OCRModeEnum = typer.Option(OCRModeEnum.FORCE, help="OCR 모드"),
    base64_encodings: str = typer.Option(
        "figure,chart,table",
        help=f"Base64로 인코딩할 요소 카테고리 목록 (쉼표로 구분) : {', '.join([e.value for e in CategoryEnum])}",
        callback=lambda x: validate_categories(x),
    ),
    ignore_element_category: str = typer.Option(
        "footer",
        "--ignore",
        help=f"파싱 결과에서 제외할 요소 카테고리 목록 (쉼표로 구분) (디폴트: footer) : {', '.join(get_literal_values(ElementCategoryType))}",
        callback=lambda x: validate_categories(x),
    ),
    is_enable_image_descriptor: bool = typer.Option(
        False,
        "--enable-image-descriptor",
        "-i",
        help=(
            "이미지 요소에 대한 자동 설명 생성 여부. 활성화하면 --base64-encodings 옵션으로 지정한 요소들에 대한 텍스트 설명을 "
            "LLM을 통해 자동으로 생성하고, Document metadata의 image_descriptions 필드에 저장합니다."
        ),
    ),
    image_descriptor_llm_vendor: LLMVendorEnum = typer.Option(
        LLMVendorEnum.OPENAI,
        "--image-descriptor-llm-vendor",
        "-e",
        help="이미지 설명 생성에 사용할 LLM Vendor",
    ),
    image_descriptor_llm_model: LLMChatModelEnum = typer.Option(
        LLMChatModelEnum.GPT_4O_MINI,
        "--image-descriptor-llm-model",
        "-q",
        help="이미지 설명 생성에 사용할 LLM 모델",
    ),
    image_descriptor_api_key: Optional[str] = typer.Option(
        None,
        "--image-descriptor-api-key",
        "-k",
        help=(
            "이미지 설명 생성에 사용할 LLM API 키. LLM 벤더에 맞게 지정해야 합니다. 미지정 시 각 벤더별 기본 "
            "환경변수(OPENAI_API_KEY, ANTHROPIC_API_KEY, UPSTAGE_API_KEY, GEMINI_API_KEY 등)에서 로딩됩니다."
        ),
    ),
    image_descriptor_base_url: Optional[str] = typer.Option(
        None,
        "--image-descriptor-base-url",
        "-r",
        help=(
            "이미지 설명 생성에 사용할 LLM API의 기본 URL. 기본 API 엔드포인트가 아닌 다른 엔드포인트를 사용하려는 경우 지정합니다. "
            "예: OpenAI 호환 API 서버, Ollama"
        ),
        callback=lambda x: validate_url(x),
    ),
    image_descriptor_temperature: Optional[float] = typer.Option(
        None,
        "--image-descriptor-temperature",
        "-t",
        help="이미지 설명 생성에 사용할 온도 값 (높을수록 다양한 응답)",
    ),
    image_descriptor_max_tokens: Optional[int] = typer.Option(
        None,
        "--image-descriptor-max-tokens",
        "-n",
        help="이미지 설명 생성의 최대 토큰 수",
    ),
    image_descriptor_language: str = typer.Option(
        LanguageEnum.KOREAN.value,
        "--image-descriptor-language",
        "-l",
        help="이미지 설명 생성에 사용할 언어",
        callback=lambda x: validate_language(x),
    ),
    is_verbose: bool = typer.Option(False, "--verbose", "-v", help="상세한 처리 정보 표시"),
    is_force: bool = typer.Option(False, "--force", "-f", help="확인 없이 출력 폴더 삭제 후 재생성"),
    is_ignore_cache: bool = typer.Option(
        False, "--ignore-cache", help="API 응답 캐시를 무시하고 항상 새로운 API 요청을 보냅니다. 캐시는 유지됩니다."
    ),
    is_cache_clear: bool = typer.Option(
        False, "--clear-cache", help="API 응답 캐시를 초기화합니다. 이전에 저장된 API 응답을 무시하고 새로 요청합니다."
    ),
    upstage_api_key: Optional[str] = typer.Option(
        None, help="Upstage API Key. 지정하지 않으면 UPSTAGE_API_KEY 환경 변수 사용"
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    is_print_version: bool = typer.Option(False, "--version", "-V", help="현재 패키지 버전 출력"),
):
    if is_print_version:
        console.print(get_version())
        raise typer.Exit()

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level, env_path=env_path)

    if upstage_api_key is None:
        upstage_api_key = os.environ.get("UPSTAGE_API_KEY")

    if not upstage_api_key:
        raise typer.BadParameter(
            "--upstage-api-key 옵션이나 UPSTAGE_API_KEY 환경 변수를 통해 Upstage API Key를 설정해주세요."
        )
    else:
        # Validate Upstage API key format
        if not upstage_api_key.startswith("up_"):
            console.print(
                "[bold red]오류: Upstage API Key 형식이 올바르지 않습니다. Upstage API Key는 'up_'로 시작합니다.[/bold red]"
            )
            raise typer.Exit(code=1)

    if input_path is None:
        console.print(
            "[bold red]오류: 입력 파일 경로가 지정되지 않았습니다. 처리할 문서 파일 경로를 지정해주세요.[/bold red]"
        )
        raise typer.Exit(1)

    is_pdf = input_path.suffix.lower() == ".pdf"

    base64_encoding_category_list = cast(list[ElementCategoryType], base64_encodings)
    ignore_element_category_list = cast(list[ElementCategoryType], ignore_element_category)

    # Check if output file exists and confirm overwrite if force option is not set
    if output_dir_path.exists():
        if is_force:
            if is_verbose:
                console.print(f"[yellow]출력 폴더 삭제 : {output_dir_path}[/yellow]")
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

    unified_document_paths = []
    for format_enum in (DocumentFormatEnum.MARKDOWN, DocumentFormatEnum.HTML, DocumentFormatEnum.TEXT):
        ext = DocumentFormatEnum.to_ext(format_enum)
        unified_output_path = output_dir_path / input_path.with_suffix(ext).name
        unified_output_path.unlink(missing_ok=True)
        unified_document_paths.append((format_enum, unified_output_path))

    # Debug: Print all arguments except api_key
    if is_verbose:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("설정", style="cyan")
        table.add_column("값", style="green")

        # Add rows to the table
        table.add_row("환경변수 파일 경로", str(env_path))
        table.add_row("입력 문서 파일 경로", str(input_path.absolute()))
        table.add_row("파일 생성 폴더", str(output_dir_path.absolute()))
        table.add_row("Document 분할 전략", document_split_strategy.value)
        table.add_row("OCR 모드", ocr_mode.value)
        table.add_row("생성할 Document 포맷", document_format.value)
        table.add_row("Base64 인코딩", ", ".join(base64_encoding_category_list))
        table.add_row("제외할 요소", ", ".join(ignore_element_category_list))
        table.add_row("통합 문서 생성 여부", "예" if is_create_unified_output else "아니오")

        # Add batch size with warning if needed
        batch_size_str = str(batch_page_size)
        if not is_pdf and batch_page_size == DEFAULT_BATCH_PAGE_SIZE:
            batch_size_str += " [yellow](경고: PDF 파일에서만 사용됩니다.)[/yellow]"
        table.add_row("배치 크기", batch_size_str)

        table.add_row("최대 페이지", str(max_page))
        table.add_row("상세 정보", "예" if is_verbose else "아니오")
        table.add_row("강제 덮어쓰기", "예" if is_force else "아니오")

        # Add image descriptor information if enabled
        if is_enable_image_descriptor:
            table.add_row("이미지 설명 활성화", "예")
            table.add_row("이미지 설명 LLM", f"{image_descriptor_llm_vendor.value} {image_descriptor_llm_model.value}")
            if image_descriptor_base_url:
                table.add_row("이미지 설명 LLM 기본 URL", image_descriptor_base_url)
            table.add_row("이미지 설명 언어", image_descriptor_language)
            if image_descriptor_temperature is not None:
                table.add_row("이미지 설명 온도", str(image_descriptor_temperature))
            if image_descriptor_max_tokens is not None:
                table.add_row("이미지 설명 최대 토큰", str(image_descriptor_max_tokens))
        else:
            table.add_row("이미지 설명 활성화", "아니오")
        # Print the table
        console.print(table)

    # Check if input file is a PDF. Warn if batch_size is specified but file is not a PDF
    if not is_pdf and batch_page_size != DEFAULT_BATCH_PAGE_SIZE and not is_verbose:
        console.print(f"[yellow]경고: 배치 크기 매개변수({batch_page_size})는 PDF가 아닌 파일에는 무시됩니다.[/yellow]")

    if is_enable_image_descriptor:
        image_descriptor = ImageDescriptor(
            llm_vendor=image_descriptor_llm_vendor,
            llm_model=image_descriptor_llm_model,
            llm_api_key=image_descriptor_api_key,
            llm_base_url=image_descriptor_base_url,
            prompt_context={"language": image_descriptor_language},
            temperature=image_descriptor_temperature,
            max_tokens=image_descriptor_max_tokens,
        )
    else:
        image_descriptor = None

    parser = UpstageDocumentParseParser(
        upstage_api_key=upstage_api_key,
        split=document_split_strategy.value,
        max_page=max_page,
        image_descriptor=image_descriptor,
        ocr_mode=ocr_mode.value,
        document_format=document_format.value,
        base64_encoding_category_list=base64_encoding_category_list,
        ignore_element_category_list=ignore_element_category_list,
        ignore_cache=is_ignore_cache,
        verbose=is_verbose,
    )

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
                for document in parser.lazy_parse(
                    django_file,
                    batch_page_size=batch_page_size,
                    ignore_validation=True,
                ):
                    f.write(json_dumps(document) + "\n")

                    if unified_document_paths:
                        for format_enum, output_path in unified_document_paths:
                            variant_page_content = document.variants.get(format_enum.value)

                            with output_path.open("at", encoding="utf-8") as uf:
                                if document_count > 0:
                                    uf.write("\n\n")
                                uf.write(variant_page_content)

                        for name, _file in document.files.items():
                            output_path = output_dir_path / name
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.open("wb").write(_file.read())

                    document_count += 1

                console.print(
                    f"[green]성공:[/green] {jsonl_output_path} 경로에 {document_count}개의 Document를 jsonl 포맷으로 생성했습니다."
                )

                if unified_document_paths:
                    for _, output_path in unified_document_paths:
                        console.print(f"[green]성공:[/green] {output_path} 경로에 통합 문서를 생성했습니다.")
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

        console.print_exception()

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


def validate_language(value: str) -> Union[LanguageEnum, str]:
    """Validates language input and returns either LanguageEnum or custom string value."""
    try:
        return LanguageEnum(value.upper())
    except ValueError:
        return value


def validate_output_formats(formats_str: str) -> List[DocumentFormatEnum]:
    """Validates and converts comma-separated format strings to DocumentFormatEnum list."""
    if not formats_str:
        return []

    valid_values: str = ", ".join(e.value for e in DocumentFormatEnum)

    # 인자값이 "-"로 시작하면 인자가 주어지지 않은 것으로 처리
    if formats_str.startswith("-"):
        raise typer.BadParameter(f"--unified-output-format (-u) 옵션 값이 누락되었습니다. 유효한 포맷 : {valid_values}")

    formats = []
    invalid_formats = []

    for fmt in formats_str.split(","):
        fmt = fmt.strip().lower()
        try:
            formats.append(DocumentFormatEnum(fmt))
        except ValueError:
            invalid_formats.append(fmt)

    if invalid_formats:
        raise typer.BadParameter(f"유효하지 않은 포맷: {', '.join(invalid_formats)}. 유효한 포맷: {valid_values}")

    return formats


def validate_url(url: Optional[str]) -> Optional[str]:
    """URL 형식의 유효성을 검사합니다."""
    if url is None:
        return None

    validator = URLValidator(schemes=("http", "https"))

    try:
        validator(url)
    except ValidationError:
        raise typer.BadParameter(f"Invalid URL Pattern : {url}")


def print_help(ctx: typer.Context) -> None:
    console.print(ctx.get_help())
    console.print(f"[dim] © {datetime.now().year} 파이썬사랑방 (기능 제안 및 컨설팅/교육 문의 : me@pyhub.kr)[/dim]")
    raise typer.Exit()
