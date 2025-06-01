"""Unified CLI for vector store operations."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from pyhub import init
from pyhub.config import DEFAULT_ENV_PATH, DEFAULT_TOML_PATH
from pyhub.llm import LLM
from pyhub.llm.types import LLMEmbeddingModelEnum

from .factory import get_vector_store, list_available_backends

# CLI 앱 생성
app = typer.Typer(
    name="rag",
    help="통합 벡터 스토어 명령어",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """RAG 벡터 스토어 관리를 위한 통합 명령어입니다."""
    if ctx.invoked_subcommand is None:
        # 서브커맨드가 없으면 help 출력
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def list_backends(
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
):
    """사용 가능한 벡터 스토어 백엔드를 나열합니다."""
    init(toml_path=toml_path, env_path=env_path)

    available = list_available_backends()

    table = Table(title="Available Vector Store Backends")
    table.add_column("Backend", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Required Dependencies")

    from .backends import list_backends as list_all_backends

    for backend_name in list_all_backends():
        try:
            from .backends import get_backend_class

            backend_class = get_backend_class(backend_name)
            deps = ", ".join(backend_class({"database_url": ""}).required_dependencies)

            if backend_name in available:
                table.add_row(backend_name, "✓ Available", deps)
            else:
                table.add_row(backend_name, "✗ Not Available", deps)
        except Exception:
            table.add_row(backend_name, "✗ Error", "Unknown")

    console.print(table)


@app.command(name="create-collection")
def create_collection(
    name: str = typer.Argument(..., help="컬렉션 이름"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="벡터 스토어 백엔드 (자동 감지)"),
    dimensions: int = typer.Option(1536, "--dimensions", "-d", help="벡터 차원"),
    distance_metric: str = typer.Option("cosine", "--distance-metric", help="거리 메트릭 (cosine, l2, inner_product)"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="데이터베이스 URL (pgvector용)"),
    db_path: Optional[Path] = typer.Option(None, "--db-path", help="데이터베이스 파일 경로 (sqlite-vec용)"),
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
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """벡터 컬렉션을 생성합니다."""
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # 설정 오버라이드
        config = {}
        if database_url:
            config["database_url"] = database_url
        if db_path:
            config["db_path"] = str(db_path)

        # 백엔드 생성
        store = get_vector_store(backend, **config)

        # 컬렉션 생성
        store.create_collection(name, dimensions, distance_metric)

        console.print(f"[green]✓ '{name}' 컬렉션을 성공적으로 생성했습니다.[/green]")
        console.print(f"[dim]백엔드: {store.backend_name}[/dim]")
        console.print(f"[dim]차원: {dimensions}[/dim]")
        console.print(f"[dim]거리 메트릭: {distance_metric}[/dim]")

    except Exception as e:
        console.print(f"[red]❌ 컬렉션 생성 실패: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="import-jsonl")
def import_jsonl(
    file_path: Path = typer.Argument(..., help="임포트할 JSONL 파일"),
    collection: str = typer.Option(..., "--collection", "-c", help="대상 컬렉션"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="벡터 스토어 백엔드 (자동 감지)"),
    batch_size: int = typer.Option(1000, "--batch-size", help="배치 크기"),
    clear: bool = typer.Option(False, "--clear", help="기존 데이터 삭제"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="데이터베이스 URL (pgvector용)"),
    db_path: Optional[Path] = typer.Option(None, "--db-path", help="데이터베이스 파일 경로 (sqlite-vec용)"),
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
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """JSONL 파일을 벡터 컬렉션으로 임포트합니다."""
    if not file_path.exists():
        console.print(f"[red]❌ 파일을 찾을 수 없습니다: {file_path}[/red]")
        raise typer.Exit(code=1)

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # 설정 오버라이드
        config = {}
        if database_url:
            config["database_url"] = database_url
        if db_path:
            config["db_path"] = str(db_path)

        # 백엔드 생성
        store = get_vector_store(backend, **config)

        # 컬렉션 확인
        if not store.collection_exists(collection):
            console.print(f"[red]❌ 컬렉션 '{collection}'이 존재하지 않습니다.[/red]")
            console.print(f"[dim]먼저 'pyhub.rag create-collection {collection}' 명령을 실행하세요.[/dim]")
            raise typer.Exit(code=1)

        # 임포트 실행
        console.print(f"[dim]'{file_path}'에서 데이터를 임포트 중...[/dim]")

        total = store.import_jsonl(collection, file_path, batch_size=batch_size, clear_existing=clear)

        console.print(f"[green]✓ {total}개의 레코드를 성공적으로 임포트했습니다.[/green]")
        console.print(f"[dim]컬렉션: {collection}[/dim]")
        console.print(f"[dim]백엔드: {store.backend_name}[/dim]")

    except Exception as e:
        console.print(f"[red]❌ 임포트 실패: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="similarity-search")
def similarity_search(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="검색할 텍스트"),
    collection: str = typer.Option(..., "--collection", "-c", help="검색할 컬렉션"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="벡터 스토어 백엔드 (자동 감지)"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL, "--model", "-m", help="임베딩 모델"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="결과 개수"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="유사도 임계값 (0-1)"),
    no_metadata: bool = typer.Option(False, "--no-metadata", help="메타데이터 숨김"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="데이터베이스 URL (pgvector용)"),
    db_path: Optional[Path] = typer.Option(None, "--db-path", help="데이터베이스 파일 경로 (sqlite-vec용)"),
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
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """벡터 유사도 검색을 수행합니다."""
    # query가 없으면 help 출력
    if query is None:
        console.print(ctx.get_help())
        raise typer.Exit()

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # 설정 오버라이드
        config = {}
        if database_url:
            config["database_url"] = database_url
        if db_path:
            config["db_path"] = str(db_path)

        # 백엔드 생성
        store = get_vector_store(backend, **config)

        # 쿼리 임베딩 생성
        console.print("[dim]쿼리 임베딩 생성 중...[/dim]")
        llm = LLM.create(model=embedding_model)
        query_embedding = llm.embed(query)

        # 검색 실행
        results = store.search(collection, query_embedding, k=limit, threshold=threshold)

        if not results:
            console.print("[yellow]검색 결과가 없습니다.[/yellow]")
        else:
            console.print(f"\n[green]검색 결과 ({len(results)}개):[/green]\n")

            for i, result in enumerate(results):
                console.print(f"[bold]#{i+1} (유사도: {result.score:.4f})[/bold]")

                if not no_metadata and result.document.metadata:
                    import json

                    console.print(f"[dim]metadata: {json.dumps(result.document.metadata, ensure_ascii=False)}[/dim]")

                console.print(result.document.page_content.strip())

                if i < len(results) - 1:
                    console.print("\n" + "-" * 50 + "\n")

    except Exception as e:
        console.print(f"[red]❌ 검색 실패: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stats(
    collection: str = typer.Argument(..., help="통계를 확인할 컬렉션"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="벡터 스토어 백엔드 (자동 감지)"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="데이터베이스 URL (pgvector용)"),
    db_path: Optional[Path] = typer.Option(None, "--db-path", help="데이터베이스 파일 경로 (sqlite-vec용)"),
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
):
    """컬렉션의 통계를 확인합니다."""
    init(toml_path=toml_path, env_path=env_path)

    try:
        # 설정 오버라이드
        config = {}
        if database_url:
            config["database_url"] = database_url
        if db_path:
            config["db_path"] = str(db_path)

        # 백엔드 생성
        store = get_vector_store(backend, **config)

        # 컬렉션 정보 가져오기
        info = store.get_collection_info(collection)

        console.print(f"\n[bold]📊 Collection Statistics: {collection}[/bold]\n")
        console.print(f"Backend: {info.get('backend', 'Unknown')}")
        console.print(f"Documents: {info.get('count', 0):,}")

        if "dimension" in info and info["dimension"]:
            console.print(f"Vector dimensions: {info['dimension']}")

        if "size" in info:
            console.print(f"Storage size: {info['size']}")

        if "db_path" in info:
            console.print(f"Database path: {info['db_path']}")

        if "indexes" in info and info["indexes"]:
            console.print("\n[bold]Indexes:[/bold]")
            for idx in info["indexes"]:
                console.print(f"  • {idx['name']} ({idx.get('type', 'Unknown')})")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(code=1)


# 더 간단한 명령어 별칭들
@app.command(name="create")  
def create_collection_simple(
    name: str = typer.Argument(..., help="컬렉션 이름"),
    dimensions: int = typer.Option(1536, "--dimensions", "-d", help="벡터 차원"),
    toml_path: Optional[Path] = typer.Option(DEFAULT_TOML_PATH, "--toml-file", help="toml 설정 파일 경로"),
    env_path: Optional[Path] = typer.Option(DEFAULT_ENV_PATH, "--env-file", help="환경 변수 파일(.env) 경로"),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """컬렉션을 생성합니다 (자동 백엔드 감지)."""
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # 자동 감지된 백엔드로 스토어 생성
        store = get_vector_store()
        
        # 컬렉션 생성
        store.create_collection(name, dimensions, "cosine")
        
        console.print(f"[green]✓ '{name}' 컬렉션을 성공적으로 생성했습니다.[/green]")
        console.print(f"[dim]백엔드: {store.backend_name}[/dim]")
        console.print(f"[dim]차원: {dimensions}[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ 컬렉션 생성 실패: {e}[/red]")
        if is_verbose:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(code=1)


@app.command(name="search")
def search_simple(
    query: str = typer.Argument(..., help="검색할 텍스트"),
    collection: str = typer.Argument(..., help="검색할 컬렉션"),
    limit: int = typer.Option(10, "--limit", "-l", help="결과 개수"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="유사도 임계값 (0-1)"),
    no_metadata: bool = typer.Option(False, "--no-metadata", help="메타데이터 숨김"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL, "--model", "-m", help="임베딩 모델"
    ),
    toml_path: Optional[Path] = typer.Option(DEFAULT_TOML_PATH, "--toml-file", help="toml 설정 파일 경로"),
    env_path: Optional[Path] = typer.Option(DEFAULT_ENV_PATH, "--env-file", help="환경 변수 파일(.env) 경로"),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """벡터 유사도 검색을 수행합니다 (자동 백엔드 감지)."""
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # 자동 감지된 백엔드로 스토어 생성
        store = get_vector_store()
        
        # 쿼리 임베딩 생성
        console.print("[dim]쿼리 임베딩 생성 중...[/dim]")
        llm = LLM.create(model=embedding_model)
        query_embedding = llm.embed(query)
        
        # 검색 실행
        results = store.search(collection, query_embedding, k=limit, threshold=threshold)
        
        if not results:
            console.print("[yellow]검색 결과가 없습니다.[/yellow]")
        else:
            console.print(f"\n[green]검색 결과 ({len(results)}개):[/green]\n")
            
            for i, result in enumerate(results):
                console.print(f"[bold]#{i+1} (유사도: {result.score:.4f})[/bold]")
                
                if not no_metadata and result.document.metadata:
                    import json
                    console.print(f"[dim]metadata: {json.dumps(result.document.metadata, ensure_ascii=False)}[/dim]")
                
                console.print(result.document.page_content.strip())
                
                if i < len(results) - 1:
                    console.print("\n" + "-" * 50 + "\n")
                    
    except Exception as e:
        console.print(f"[red]❌ 검색 실패: {e}[/red]")
        if is_verbose:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(code=1)


@app.command(name="load")
def load_simple(
    file_path: Path = typer.Argument(..., help="임포트할 JSONL 파일"),
    collection: str = typer.Argument(..., help="대상 컬렉션"),
    batch_size: int = typer.Option(1000, "--batch-size", help="배치 크기"),
    clear: bool = typer.Option(False, "--clear", help="기존 데이터 삭제"),
    toml_path: Optional[Path] = typer.Option(DEFAULT_TOML_PATH, "--toml-file", help="toml 설정 파일 경로"),
    env_path: Optional[Path] = typer.Option(DEFAULT_ENV_PATH, "--env-file", help="환경 변수 파일(.env) 경로"),
    is_verbose: bool = typer.Option(False, "--verbose"),
):
    """JSONL 파일을 벡터 컬렉션으로 임포트합니다 (자동 백엔드 감지)."""
    if not file_path.exists():
        console.print(f"[red]❌ 파일을 찾을 수 없습니다: {file_path}[/red]")
        raise typer.Exit(code=1)
        
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # 자동 감지된 백엔드로 스토어 생성
        store = get_vector_store()
        
        # 컬렉션 확인
        if not store.collection_exists(collection):
            console.print(f"[red]❌ 컬렉션 '{collection}'이 존재하지 않습니다.[/red]")
            console.print(f"[dim]먼저 'pyhub.rag create {collection}' 명령을 실행하세요.[/dim]")
            raise typer.Exit(code=1)
            
        # 임포트 실행
        console.print(f"[dim]'{file_path}'에서 데이터를 임포트 중...[/dim]")
        
        total = store.import_jsonl(collection, file_path, batch_size=batch_size, clear_existing=clear)
        
        console.print(f"[green]✓ {total}개의 레코드를 성공적으로 임포트했습니다.[/green]")
        console.print(f"[dim]컬렉션: {collection}[/dim]")
        console.print(f"[dim]백엔드: {store.backend_name}[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ 임포트 실패: {e}[/red]")
        if is_verbose:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(code=1)
