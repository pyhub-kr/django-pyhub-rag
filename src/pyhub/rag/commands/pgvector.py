import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer
from rich.console import Console

from pyhub import init
from pyhub.config import DEFAULT_ENV_PATH, DEFAULT_TOML_PATH
from pyhub.llm.types import EmbeddingDimensionsEnum, LLMEmbeddingModelEnum

# Create pgvector subcommand group
app = typer.Typer(
    name="pgvector",
    help="PostgreSQL pgvector 관련 명령어",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def pgvector_callback(ctx: typer.Context):
    """PostgreSQL pgvector 벡터 데이터베이스 관리를 위한 서브커맨드입니다."""
    if ctx.invoked_subcommand is None:
        # 서브커맨드가 없으면 help 출력
        console.print(ctx.get_help())
        raise typer.Exit()


def get_database_url(
    database_url: Optional[str] = None,
    database_alias: Optional[str] = None,
) -> str:
    """데이터베이스 URL을 결정합니다.

    우선순위:
    1. 직접 지정된 database_url
    2. Django 설정의 database_alias
    3. 환경변수 (PGVECTOR_DATABASE_URL, VECTOR_DATABASE_URL, DATABASE_URL)
    """
    # 1. 직접 지정된 URL
    if database_url:
        return database_url

    # 2. Django 설정에서 별칭으로 찾기
    if database_alias:
        from django.conf import settings

        if database_alias in settings.DATABASES:
            db_config = settings.DATABASES[database_alias]
            if "postgresql" not in db_config.get("ENGINE", ""):
                raise typer.BadParameter(f"Database alias '{database_alias}' is not a PostgreSQL database")
            # Django 설정을 URL로 변환
            return build_database_url_from_config(db_config)
        else:
            raise typer.BadParameter(f"Database alias '{database_alias}' not found")

    # 3. 환경변수에서 찾기
    for env_var in ["PGVECTOR_DATABASE_URL", "VECTOR_DATABASE_URL", "DATABASE_URL"]:
        if url := os.environ.get(env_var):
            if url.startswith("postgresql://") or url.startswith("postgres://"):
                return url

    # 4. Django 설정에서 PostgreSQL DB 찾기
    try:
        from django.conf import settings

        for alias, config in settings.DATABASES.items():
            if "postgresql" in config.get("ENGINE", ""):
                console.print(f"[dim]Using Django database '{alias}'[/dim]")
                return build_database_url_from_config(config)
    except:
        pass

    raise typer.BadParameter(
        "PostgreSQL database URL not found. " "Please specify --database-url or set DATABASE_URL environment variable"
    )


def build_database_url_from_config(config: dict) -> str:
    """Django 데이터베이스 설정을 URL로 변환"""
    user = config.get("USER", "")
    password = config.get("PASSWORD", "")
    host = config.get("HOST", "localhost")
    port = config.get("PORT", "5432")
    dbname = config.get("NAME", "")

    auth = f"{user}:{password}@" if user else ""
    return f"postgresql://{auth}{host}:{port}/{dbname}"


@app.command()
def check(
    database_url: Optional[str] = typer.Option(
        None, "--database-url", "-e", help="PostgreSQL 연결 URL", envvar="DATABASE_URL"
    ),
    database_alias: str = typer.Option("default", "--database", "-d", help="Django 데이터베이스 별칭"),
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
    """pgvector 확장이 설치되어 있는지 확인합니다."""

    init(toml_path=toml_path, env_path=env_path)

    try:
        import psycopg2
    except ImportError:
        console.print("[red]❌ psycopg2 패키지가 설치되어 있지 않습니다.[/red]")
        console.print("[dim]설치: pip install psycopg2-binary[/dim]")
        raise typer.Exit(code=1)

    db_url = get_database_url(database_url, database_alias)

    try:
        # URL 파싱
        parsed = urlparse(db_url)
        console.print(f"[dim]Connecting to {parsed.hostname}:{parsed.port}/{parsed.path[1:]}...[/dim]")

        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # pgvector 확장 확인
        cursor.execute("SELECT installed_version FROM pg_available_extensions WHERE name = 'vector'")
        result = cursor.fetchone()

        if result and result[0]:
            console.print(f"[green]✓ pgvector {result[0]} is installed[/green]")

            # 벡터 테이블 수 확인
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE data_type = 'USER-DEFINED' 
                AND udt_name = 'vector'
            """
            )
            vector_columns = cursor.fetchone()[0]
            console.print(f"[dim]  Vector columns found: {vector_columns}[/dim]")

        else:
            console.print("[yellow]⚠️  pgvector extension is not installed[/yellow]")
            console.print("[dim]  Run: CREATE EXTENSION vector;[/dim]")
            raise typer.Exit(code=1)

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        console.print(f"[red]❌ Database connection failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="install-extension")
def install_extension(
    database_url: Optional[str] = typer.Option(
        None, "--database-url", "-e", help="PostgreSQL 연결 URL", envvar="DATABASE_URL"
    ),
    database_alias: str = typer.Option("default", "--database", "-d", help="Django 데이터베이스 별칭"),
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
    """pgvector 확장을 설치합니다 (CREATE EXTENSION vector)."""

    init(toml_path=toml_path, env_path=env_path)

    try:
        import psycopg2
    except ImportError:
        console.print("[red]❌ psycopg2 패키지가 설치되어 있지 않습니다.[/red]")
        raise typer.Exit(code=1)

    db_url = get_database_url(database_url, database_alias)

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # 확장 설치
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()

        # 버전 확인
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        version = cursor.fetchone()[0]

        console.print(f"[green]✓ pgvector {version} extension installed successfully[/green]")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        console.print(f"[red]❌ Failed to install extension: {e}[/red]")
        if "permission denied" in str(e).lower():
            console.print("[dim]  You may need superuser privileges[/dim]")
        raise typer.Exit(code=1)


@app.command(name="create-table")
def create_table(
    table_name: str = typer.Argument(..., help="생성할 테이블 이름"),
    database_url: Optional[str] = typer.Option(
        None, "--database-url", "-e", help="PostgreSQL 연결 URL", envvar="DATABASE_URL"
    ),
    database_alias: str = typer.Option("default", "--database", "-d", help="Django 데이터베이스 별칭"),
    dimensions: EmbeddingDimensionsEnum = typer.Option(
        EmbeddingDimensionsEnum.D_1536, "--dimensions", help="벡터 차원"
    ),
    index_type: str = typer.Option("hnsw", "--index-type", help="인덱스 타입 (hnsw, ivfflat)"),
    distance_metric: str = typer.Option("cosine", "--distance-metric", help="거리 메트릭 (cosine, l2, inner_product)"),
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
    """PostgreSQL에 pgvector 테이블을 생성합니다."""

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        import psycopg2
    except ImportError:
        console.print("[red]❌ psycopg2 패키지가 설치되어 있지 않습니다.[/red]")
        raise typer.Exit(code=1)

    db_url = get_database_url(database_url, database_alias)

    # 거리 함수 매핑
    distance_ops = {"cosine": "vector_cosine_ops", "l2": "vector_l2_ops", "inner_product": "vector_ip_ops"}

    if distance_metric not in distance_ops:
        console.print(f"[red]❌ Invalid distance metric: {distance_metric}[/red]")
        raise typer.Exit(code=1)

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # 테이블 생성
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            page_content TEXT NOT NULL,
            metadata JSONB,
            embedding vector({dimensions.value})
        )
        """

        cursor.execute(create_sql)

        # 인덱스 생성
        if index_type == "hnsw":
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
            ON {table_name} 
            USING hnsw (embedding {distance_ops[distance_metric]})
            """
        else:  # ivfflat
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
            ON {table_name} 
            USING ivfflat (embedding {distance_ops[distance_metric]})
            WITH (lists = 100)
            """

        cursor.execute(index_sql)
        conn.commit()

        # 데이터베이스 정보
        parsed = urlparse(db_url)
        console.print(f"[green]✓ '{table_name}' 테이블을 성공적으로 생성했습니다.[/green]")
        console.print(f"[dim]데이터베이스: {parsed.hostname}:{parsed.port}/{parsed.path[1:]}[/dim]")
        console.print(f"[dim]인덱스 타입: {index_type} ({distance_metric})[/dim]")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        if "already exists" in str(e):
            console.print(f"[red]❌ 테이블 생성 실패: '{table_name}' 테이블이 이미 존재합니다.[/red]")
            parsed = urlparse(db_url)
            console.print(f"[dim]데이터베이스: {parsed.hostname}:{parsed.port}/{parsed.path[1:]}[/dim]")
        else:
            console.print(f"[red]❌ Error creating table: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="import-jsonl")
def import_jsonl(
    jsonl_path: Path = typer.Argument(..., help="임포트할 JSONL 파일"),
    database_url: Optional[str] = typer.Option(
        None, "--database-url", "-e", help="PostgreSQL 연결 URL", envvar="DATABASE_URL"
    ),
    database_alias: str = typer.Option("default", "--database", "-d", help="Django 데이터베이스 별칭"),
    table_name: str = typer.Option(..., "--table", "-t", help="대상 테이블 이름"),
    batch_size: int = typer.Option(1000, "--batch-size", help="배치 크기"),
    clear: bool = typer.Option(False, "--clear", "-c", help="기존 데이터 삭제"),
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
    """JSONL 파일을 PostgreSQL pgvector 테이블로 임포트합니다."""

    if not jsonl_path.exists():
        console.print(f"[red]❌ 파일을 찾을 수 없습니다: {jsonl_path}[/red]")
        raise typer.Exit(code=1)

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        import json

        import psycopg2
        import psycopg2.extras
    except ImportError:
        console.print("[red]❌ psycopg2 패키지가 설치되어 있지 않습니다.[/red]")
        raise typer.Exit(code=1)

    db_url = get_database_url(database_url, database_alias)

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # 테이블 존재 확인
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (table_name,))
        if not cursor.fetchone()[0]:
            console.print(f"[red]❌ 테이블 '{table_name}'이 존재하지 않습니다.[/red]")
            console.print(f"[dim]먼저 'pyhub.rag pgvector create-table {table_name}' 명령을 실행하세요.[/dim]")
            raise typer.Exit(code=1)

        # 기존 데이터 삭제
        if clear:
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            console.print("[yellow]기존 데이터를 삭제했습니다.[/yellow]")

        # JSONL 파일 읽기 및 임포트
        total = 0
        batch = []

        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())

                # 데이터 검증
                if "page_content" not in data or "embedding" not in data:
                    console.print(f"[yellow]⚠️  Invalid data format at line {total + 1}[/yellow]")
                    continue

                batch.append((data["page_content"], json.dumps(data.get("metadata", {})), data["embedding"]))

                # 배치 처리
                if len(batch) >= batch_size:
                    psycopg2.extras.execute_batch(
                        cursor,
                        f"""
                        INSERT INTO {table_name} (page_content, metadata, embedding)
                        VALUES (%s, %s::jsonb, %s::vector)
                        """,
                        batch,
                    )
                    total += len(batch)
                    console.print(f"[dim]Imported {total} records...[/dim]")
                    batch = []

        # 남은 데이터 처리
        if batch:
            psycopg2.extras.execute_batch(
                cursor,
                f"""
                INSERT INTO {table_name} (page_content, metadata, embedding)
                VALUES (%s, %s::jsonb, %s::vector)
                """,
                batch,
            )
            total += len(batch)

        conn.commit()

        parsed = urlparse(db_url)
        console.print(f"[green]✓ {total}개의 레코드를 성공적으로 임포트했습니다.[/green]")
        console.print(f"[dim]테이블: {table_name}[/dim]")
        console.print(f"[dim]데이터베이스: {parsed.hostname}:{parsed.port}/{parsed.path[1:]}[/dim]")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        console.print(f"[red]❌ Import failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="similarity-search")
def similarity_search(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="검색할 텍스트"),
    database_url: Optional[str] = typer.Option(
        None, "--database-url", "-e", help="PostgreSQL 연결 URL", envvar="DATABASE_URL"
    ),
    database_alias: str = typer.Option("default", "--database", "-d", help="Django 데이터베이스 별칭"),
    table_name: str = typer.Option(..., "--table", "-t", help="검색할 테이블"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL, "--model", "-m", help="임베딩 모델"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="결과 개수"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="유사도 임계값 (0-1)"),
    distance_metric: str = typer.Option("cosine", "--distance-metric", help="거리 메트릭 (cosine, l2, inner_product)"),
    no_metadata: bool = typer.Option(False, "--no-metadata", help="메타데이터 숨김"),
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
    """PostgreSQL pgvector에서 유사도 검색을 수행합니다."""

    # query가 없으면 help 출력
    if query is None:
        console.print(ctx.get_help())
        raise typer.Exit()

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        import json

        import psycopg2

        from pyhub.llm import LLM
    except ImportError as e:
        console.print(f"[red]❌ Required package not found: {e}[/red]")
        raise typer.Exit(code=1)

    db_url = get_database_url(database_url, database_alias)

    # 거리 함수 매핑
    distance_funcs = {"cosine": "<=>", "l2": "<->", "inner_product": "<#>"}

    if distance_metric not in distance_funcs:
        console.print(f"[red]❌ Invalid distance metric: {distance_metric}[/red]")
        raise typer.Exit(code=1)

    try:
        # 쿼리 임베딩 생성
        console.print("[dim]Generating embedding for query...[/dim]")
        llm = LLM.create(model=embedding_model)
        query_embedding = llm.embed(query)

        # 데이터베이스 검색
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # 유사도 검색 쿼리
        search_sql = f"""
        SELECT 
            page_content,
            metadata,
            1 - (embedding {distance_funcs[distance_metric]} %s::vector) as similarity
        FROM {table_name}
        WHERE 1 = 1
        """

        params = [query_embedding]

        # 임계값 조건 추가
        if threshold is not None:
            search_sql += f" AND 1 - (embedding {distance_funcs[distance_metric]} %s::vector) >= %s"
            params.append(query_embedding)
            params.append(threshold)

        search_sql += f"""
        ORDER BY embedding {distance_funcs[distance_metric]} %s::vector
        LIMIT %s
        """
        params.extend([query_embedding, limit])

        cursor.execute(search_sql, params)
        results = cursor.fetchall()

        if not results:
            console.print("[yellow]검색 결과가 없습니다.[/yellow]")
        else:
            console.print(f"\n[green]검색 결과 ({len(results)}개):[/green]\n")

            for i, (content, metadata, similarity) in enumerate(results):
                console.print(f"[bold]#{i+1} (유사도: {similarity:.4f})[/bold]")

                if not no_metadata and metadata:
                    console.print(f"[dim]metadata: {json.dumps(metadata, ensure_ascii=False)}[/dim]")

                console.print(content.strip())

                if i < len(results) - 1:
                    console.print("\n" + "-" * 50 + "\n")

        cursor.close()
        conn.close()

    except Exception as e:
        console.print(f"[red]❌ Search failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stats(
    table_name: str = typer.Argument(..., help="통계를 확인할 테이블"),
    database_url: Optional[str] = typer.Option(
        None, "--database-url", "-e", help="PostgreSQL 연결 URL", envvar="DATABASE_URL"
    ),
    database_alias: str = typer.Option("default", "--database", "-d", help="Django 데이터베이스 별칭"),
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
    """테이블의 벡터 통계를 확인합니다."""

    init(toml_path=toml_path, env_path=env_path)

    try:
        import psycopg2
    except ImportError:
        console.print("[red]❌ psycopg2 패키지가 설치되어 있지 않습니다.[/red]")
        raise typer.Exit(code=1)

    db_url = get_database_url(database_url, database_alias)

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # 테이블 정보
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]

        # 벡터 차원
        cursor.execute(
            f"""
            SELECT 
                dimension(embedding) as dim
            FROM {table_name}
            LIMIT 1
        """
        )
        result = cursor.fetchone()
        dimensions = result[0] if result else 0

        # 인덱스 정보
        cursor.execute(
            """
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = %s
            AND indexdef LIKE '%embedding%'
        """,
            (table_name,),
        )
        indexes = cursor.fetchall()

        # 테이블 크기
        cursor.execute(
            """
            SELECT 
                pg_size_pretty(pg_total_relation_size(%s::regclass))
        """,
            (table_name,),
        )
        table_size = cursor.fetchone()[0]

        # 출력
        console.print(f"\n[bold]📊 Table Statistics: {table_name}[/bold]\n")
        console.print(f"Total rows: {total_rows:,}")
        console.print(f"Vector dimensions: {dimensions}")
        console.print(f"Table size: {table_size}")

        if indexes:
            console.print("\n[bold]Indexes:[/bold]")
            for idx_name, idx_def in indexes:
                console.print(f"  • {idx_name}")
                if "hnsw" in idx_def:
                    console.print("    [dim]Type: HNSW[/dim]")
                elif "ivfflat" in idx_def:
                    console.print("    [dim]Type: IVFFlat[/dim]")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(code=1)
