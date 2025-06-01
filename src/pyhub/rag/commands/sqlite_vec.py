import logging
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pyhub import init
from pyhub.config import DEFAULT_ENV_PATH, DEFAULT_TOML_PATH
from pyhub.llm.types import EmbeddingDimensionsEnum, LLMEmbeddingModelEnum
from pyhub.rag.db.sqlite_vec import (
    DistanceMetric,
    SQLiteVecError,
    create_virtual_table,
    import_jsonl,
    load_extensions,
    similarity_search,
)

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

# Create SQLite-vec subcommand group
app = typer.Typer(
    name="sqlite-vec",
    help="SQLite-vec 관련 명령어",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def sqlite_vec_callback(ctx: typer.Context):
    """SQLite-vec 벡터 데이터베이스 관리를 위한 서브커맨드입니다."""
    if ctx.invoked_subcommand is None:
        # 서브커맨드가 없으면 help 출력
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def check():
    """
    sqlite-vec 확장이 제대로 로드될 수 있는지 확인합니다.

    이 명령어는 다음을 확인합니다:
    1. 시스템 아키텍처가 호환되는지 (Windows ARM은 지원되지 않음)
    2. Python 버전이 3.10 이상인지 (sqlite-vec에 필요)
    3. sqlite-vec 라이브러리가 설치되어 있는지
    4. 현재 Python 설치가 SQLite 확장을 지원하는지

    확인 중 하나라도 실패하면 오류 코드 1로 종료하고, 그렇지 않으면 성공적인 설정을 확인합니다.
    """

    is_windows = sys.platform == "win32"
    is_arm = "ARM" in sys.version
    is_python_3_10_or_later = sys.version_info[:2] >= (3, 10)

    if is_windows and is_arm:
        console.print(
            "[bold red]ARM 버전의 Python은 sqlite-vec 라이브러리를 지원하지 않습니다. AMD64 버전의 Python을 다시 설치해주세요.[/bold red]"
        )
        raise typer.Exit(code=1)

    if not is_python_3_10_or_later:
        console.print("[bold red]Python 3.10 이상이 필요합니다.[/bold red]")
        raise typer.Exit(code=1)

    if sqlite_vec is None:
        console.print("[bold red]sqlite-vec 라이브러리를 설치해주세요.[/bold red]")
        raise typer.Exit(code=1)

    with sqlite3.connect(":memory:") as db:
        try:
            load_extensions(db)
        except AttributeError:
            console.print(
                f"[bold red]{sys.executable} 은 sqlite3 확장을 지원하지 않습니다. 가이드를 참고하여 Python을 다시 설치해주세요.[/bold red]"
            )
            raise typer.Exit(code=1)
        else:
            console.print(f"[bold green]{sys.executable} 은 sqlite3 확장을 지원합니다.[/bold green]")
            console.print("[bold green]sqlite-vec 확장이 정상적으로 작동합니다.[/bold green]")


@app.command(name="create-table")
def command_create_table(
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="SQLite DB 경로"),
    table_name: str = typer.Argument("documents", help="테이블 이름"),
    dimensions: EmbeddingDimensionsEnum = typer.Option(
        EmbeddingDimensionsEnum.D_1536, help="벡터 테이블의 임베딩 차원"
    ),
    distance_metric: DistanceMetric = typer.Option(DistanceMetric.COSINE, help="유사도 검색을 위한 거리 메트릭"),
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
    is_verbose: bool = typer.Option(False, "--verbose", help="추가 디버그 정보 출력"),
):
    """
    SQLite 데이터베이스에 sqlite-vec 확장을 사용하여 벡터 테이블을 생성합니다.
    """

    if not db_path.suffix:
        db_path = db_path.with_suffix(".sqlite3")
        console.print(f"[yellow]파일 확장자가 제공되지 않았습니다. '{db_path}'를 사용합니다.[/yellow]")

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        create_virtual_table(
            db_path=db_path,
            table_name=table_name,
            dimensions=dimensions,
            distance_metric=distance_metric,
        )
    except SQLiteVecError as e:
        error_msg = str(e)
        if "이미 존재합니다" in error_msg:
            lines = error_msg.split("\n")
            console.print(f"[red]❌ {lines[0]}[/red]")
            if len(lines) > 1:
                console.print(f"[dim]{lines[1]}[/dim]")
            console.print("\n[yellow]💡 해결 방법:[/yellow]")
            console.print("  • 다른 테이블 이름을 사용하세요")
            console.print("  • 기존 테이블을 삭제하려면 SQLite 클라이언트를 사용하세요")
            console.print("  • 기존 데이터를 유지하려면 import-jsonl 명령을 사용하세요")
        else:
            console.print(f"[red]❌ {error_msg}[/red]")
        raise typer.Exit(code=1)
    else:
        # 절대 경로로 변환
        abs_db_path = db_path.resolve()
        console.print(f"[bold green]✓ '{table_name}' 가상 테이블을 성공적으로 생성했습니다.[/bold green]")
        console.print(f"[dim]데이터베이스: {abs_db_path}[/dim]")


@app.command(name="import-jsonl")
def command_import_jsonl(
    jsonl_path: Path = typer.Argument(..., help="임베딩이 포함된 JSONL 파일 경로"),
    db_path: Path = typer.Option(Path("db.sqlite3"), "--db-path", "-d", help="SQLite DB 경로"),
    table_name: str = typer.Option(None, "--table", "-t", help="테이블 이름 (선택사항, 미지정시 자동 감지)"),
    clear: bool = typer.Option(False, "--clear", "-c", help="로딩 전 테이블의 기존 데이터 삭제"),
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
    is_verbose: bool = typer.Option(False, "--verbose", help="추가 디버그 정보 출력"),
):
    """
    JSONL 파일의 벡터 데이터를 SQLite 데이터베이스 테이블로 로드합니다.
    """

    if not db_path.exists():
        console.print(f"Not found : {db_path}")
        raise typer.Exit(code=1)

    if table_name and "sqlite3" in table_name:
        console.print(f"[red]Invalid table name : {table_name}[/red]")
        raise typer.Exit(code=1)

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    console.print(f"{db_path} 경로의 {table_name} 테이블에 {jsonl_path} 데이터를 임포트합니다.")

    try:
        import_jsonl(
            db_path=db_path,
            table_name=table_name,
            jsonl_path=jsonl_path,
            clear=clear,
        )
    except SQLiteVecError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="similarity-search")
def command_similarity_search(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="유사한 문서를 검색할 텍스트"),
    db_path: Path = typer.Option(Path("db.sqlite3"), "--db-path", "-d", help="SQLite DB 경로"),
    table_name: str = typer.Option(None, "--table", "-t", help="테이블 이름 (선택사항, 미지정시 자동 감지)"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL, help="사용할 임베딩 모델"
    ),
    limit: int = typer.Option(4, help="반환할 최대 결과 수"),
    no_metadata: bool = typer.Option(False, help="결과에서 메타데이터 숨김"),
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
    is_verbose: bool = typer.Option(False, "--verbose", help="추가 디버그 정보 출력"),
):
    """
    SQLite 벡터 데이터베이스에서 의미적 유사도 검색을 수행합니다.
    """

    # query가 없으면 help 출력
    if query is None:
        console.print(ctx.get_help())
        raise typer.Exit()

    if not db_path.exists():
        console.print(f"Not found : {db_path}")
        raise typer.Exit(code=1)

    if is_verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        doc_list = similarity_search(
            db_path=db_path,
            table_name=table_name,
            query=query,
            embedding_model=embedding_model,
            limit=limit,
        )

        for i, doc in enumerate(doc_list):
            if not no_metadata:
                console.print(f"metadata: {doc.metadata}\n")
            console.print(doc.page_content.strip())
            if i < len(doc_list) - 1:
                console.print("\n----\n")
    except SQLiteVecError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
