import logging
import sqlite3
import sys
from pathlib import Path

import typer
from rich.console import Console

from pyhub.llm.enum import EmbeddingDimensionsEnum, LLMEmbeddingModelEnum
from pyhub.logger import LogCapture
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
app = typer.Typer(name="sqlite-vec", help="Commands related to SQLite-vec")
console = Console()


@app.command()
def check():
    """
    Check if sqlite-vec extension can be loaded properly.

    This command verifies:
    1. If the system architecture is compatible (Windows ARM is not supported)
    2. If Python version is 3.10 or later (required for sqlite-vec)
    3. If the sqlite-vec library is installed
    4. If the current Python installation supports SQLite extensions

    Exits with error code 1 if any check fails, otherwise confirms successful setup.
    """

    is_windows = sys.platform == "win32"
    is_arm = "ARM" in sys.version
    is_python_3_10_or_later = sys.version_info[:2] >= (3, 10)

    if is_windows and is_arm:
        console.print(
            "[bold red]ARM version of Python does not support sqlite-vec library. Please reinstall AMD64 version of Python.[/bold red]"
        )
        raise typer.Exit(code=1)

    if not is_python_3_10_or_later:
        console.print("[bold red]Python 3.10 or later is required.[/bold red]")
        raise typer.Exit(code=1)

    if sqlite_vec is None:
        console.print("[bold red]Please install sqlite-vec library.[/bold red]")
        raise typer.Exit(code=1)

    with sqlite3.connect(":memory:") as db:
        try:
            load_extensions(db)
        except AttributeError:
            console.print(
                "[bold red]This Python does not support sqlite3 extension. Please refer to the guide and reinstall Python.[/bold red]"
            )
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]This Python supports sqlite3 extension.[/bold green]")
            console.print("[bold green]sqlite-vec extension is working properly.[/bold green]")


@app.command(name="create-table")
def command_create_table(
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="sqlite db path"),
    table_name: str = typer.Argument("documents", help="table name"),
    dimensions: EmbeddingDimensionsEnum = typer.Option(
        EmbeddingDimensionsEnum.D_1536, help="Embedding dimensions for the vector table"
    ),
    distance_metric: DistanceMetric = typer.Option(DistanceMetric.COSINE, help="Distance metric for similarity search"),
    verbose: bool = typer.Option(False, help="Print additional debug information"),
):
    """
    Create a vector table using sqlite-vec extension in SQLite database.
    """

    if not db_path.suffix:
        db_path = db_path.with_suffix(".sqlite3")
        console.print(f"[yellow]No file extension provided. Using '{db_path}'[/yellow]")

    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    with LogCapture(console=console, level=log_level):
        try:
            create_virtual_table(
                db_path=db_path,
                table_name=table_name,
                dimensions=dimensions,
                distance_metric=distance_metric,
            )
        except SQLiteVecError as e:
            console.print(f"[red]{e}")
            raise typer.Exit(code=1)
        else:
            console.print(f"[bold green]Successfully created virtual table '{table_name}' in {db_path}[/bold green]")


@app.command(name="import-jsonl")
def command_import_jsonl(
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="sqlite db path"),
    table_name: str = typer.Argument(None, help="table name (optional, auto-detected if not provided)"),
    jsonl_path: Path = typer.Option(..., help="Path to the JSONL file with embeddings"),
    clear: bool = typer.Option(False, help="Clear existing data in the table before loading"),
    verbose: bool = typer.Option(False, help="Print additional debug information"),
):
    """
    Load vector data from JSONL file into SQLite database table.
    """

    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    with LogCapture(console=console, level=log_level):
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
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="Path to the SQLite database"),
    table_name: str = typer.Argument(None, help="Name of the table to query"),
    query: str = typer.Option(..., help="Text to search for similar documents"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL, help="Embedding model to use"
    ),
    limit: int = typer.Option(4, help="Maximum number of results to return"),
    no_metadata: bool = typer.Option(False, help="Hide metadata in the results"),
    verbose: bool = typer.Option(False, help="Print additional debug information"),
):
    """
    Perform a semantic similarity search in a SQLite vector database.
    """

    if verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    with LogCapture(console=console, level=log_level):
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
