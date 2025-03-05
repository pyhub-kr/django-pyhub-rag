import contextlib
import functools
import sqlite3
import sys
from enum import Enum
from pathlib import Path
from typing import Generator, Optional

import typer
from rich.console import Console

from pyhub.llm import LLM
from pyhub.llm.enum import EmbeddingDimensionsEnum, LLMEmbeddingModelEnum
from pyhub.rag.json import JSONDecodeError, json_dumps, json_loads

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

# Create SQLite-vec subcommand group
app = typer.Typer(name="sqlite-vec", help="Commands related to SQLite-vec")
console = Console()


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    L1 = "L1"
    L2 = "L2"


class SQLiteVecError(Exception):
    """Base exception class for SQLite-vec related errors"""

    pass


def load_extensions(conn: sqlite3.Connection):
    """Load sqlite_vec extension to the SQLite connection"""

    if sqlite_vec is None:
        console.print("[bold red]Please install sqlite-vec library.[/bold red]")
        console.print("[bold yellow]Or check if you're using the correct virtual environment.[/bold yellow]")
        raise typer.Exit(code=1)

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


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


@contextlib.contextmanager
def get_db_cursor(db_path: Path, debug: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager that provides a SQLite cursor with sqlite-vec extension loaded.

    Args:
        db_path: Path to SQLite database
        debug: If True, prints SQL statements being executed

    Yields:
        sqlite3.Cursor: Database cursor with sqlite-vec extension loaded

    Raises:
        SQLiteVecError: If sqlite-vec extension cannot be loaded
    """
    with sqlite3.connect(db_path) as conn:
        load_extensions(conn)

        if debug:

            def sql_trace_callback(sql):
                console.print(f"[dim blue]Executing: {sql}[/dim blue]")

            conn.set_trace_callback(sql_trace_callback)

        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()


@app.command()
def create_table(
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="sqlite db path"),
    table_name: str = typer.Argument("documents", help="table name"),
    dimensions: EmbeddingDimensionsEnum = typer.Option(
        EmbeddingDimensionsEnum.D_1536, help="Embedding dimensions for the vector table"
    ),
    distance_metric: DistanceMetric = typer.Option(DistanceMetric.COSINE, help="Distance metric for similarity search"),
):
    """
    Create a vector table using sqlite-vec extension in SQLite database.

    This command:
    1. Connects to the specified SQLite database (adds .sqlite3 extension if none provided)
    2. Loads the sqlite-vec extension
    3. Creates a virtual table with the specified name and configuration
    4. Sets up the table schema with id, page_content, metadata, and embedding columns
    5. Configures the embedding vector dimensions and distance metric

    The created table will support vector similarity searches using the specified distance metric.
    """

    if not db_path.suffix:
        db_path = db_path.with_suffix(".sqlite3")
        console.print(f"[yellow]No file extension provided. Using '{db_path}'[/yellow]")

    sql = f"""
    CREATE VIRTUAL TABLE {table_name} using vec0(
        id integer PRIMARY KEY AUTOINCREMENT, 
        page_content text NOT NULL, 
        metadata text NOT NULL CHECK ((JSON_VALID(metadata) OR metadata IS NULL)), 
        embedding float[{dimensions.value}] distance_metric={distance_metric.value}
    )
    """

    with get_db_cursor(db_path) as cursor:
        # Print the SQL query for informational purposes
        console.print("[blue]Executing SQL:[/blue]")
        console.print(f"[cyan]{sql}[/cyan]")

        try:
            cursor.execute(sql)
        except sqlite3.OperationalError as e:
            console.print(f"[red]{e} (db_path: {db_path}[/red]")
            raise typer.Exit(code=1)

        console.print(f"[bold green]Successfully created virtual table '{table_name}' in {db_path}[/bold green]")


@app.command()
def import_jsonl(
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="sqlite db path"),
    table_name: str = typer.Argument(None, help="table name (optional, auto-detected if not provided)"),
    jsonl_path: Path = typer.Option(..., help="Path to the JSONL file with embeddings"),
    clear: bool = typer.Option(False, help="Clear existing data in the table before loading"),
    debug: bool = typer.Option(False, help="Print SQL statements being executed"),
):
    """
    Load vector data from JSONL file into SQLite database table.

    This command:
    1. Connects to the specified SQLite database
    2. Loads the sqlite-vec extension
    3. Optionally clears existing data from the table if --clear is specified
    4. Reads the JSONL file line by line, processing each record
    5. Validates each record has required fields (page_content and embedding)
    6. Inserts valid records into the database table
    7. Shows progress during the operation
    8. Reports summary statistics upon completion

    Each JSONL record should contain at minimum 'page_content' and 'embedding' fields.
    The 'metadata' field is optional and will be stored as a JSON string.

    If table_name is not provided, the command will automatically detect a table with an embedding column.
    If exactly one such table is found, it will be used. If none or multiple tables are found, an error will be raised.
    """

    with get_db_cursor(db_path, debug) as cursor:
        # Auto-detect table with embedding column if table_name is not provided
        if table_name is None:
            try:
                # Find tables with embedding column
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%embedding%'")
                tables = cursor.fetchall()

                if not tables:
                    console.print("[red]Error: No tables with embedding column found in the database[/red]")
                    raise typer.Exit(code=1)

                if len(tables) > 1:
                    table_list = ", ".join([t[0] for t in tables])
                    console.print(f"[red]Error: Multiple tables with embedding column found: {table_list}[/red]")
                    console.print("[red]Please specify a table name explicitly[/red]")
                    raise typer.Exit(code=1)

                table_name = tables[0][0]
                console.print(f"[green]Auto-detected table: '{table_name}'[/green]")

            except sqlite3.Error as e:
                console.print(f"[red]Error detecting tables: {str(e)}[/red]")
                raise typer.Exit(code=1)

        # Clear existing data if requested
        if clear:
            try:
                cursor.execute(f"DELETE FROM {table_name}")
                deleted_count = cursor.rowcount
                console.print(f"[yellow]Cleared {deleted_count} existing records from table '{table_name}'[/yellow]")
            except sqlite3.Error as e:
                console.print(f"[red]Error clearing table: {str(e)}[/red]")
                raise typer.Exit(code=1)

        # Read and insert data from JSONL
        with jsonl_path.open("r", encoding="utf-8") as f:
            total_lines = sum(1 for __ in f)
            f.seek(0)

            console.print(f"Found {total_lines} records in JSONL file")

            inserted_count = 0
            for i, line in enumerate(f):
                try:
                    data = json_loads(line.strip())

                    # Check required fields
                    if "page_content" not in data:
                        console.print(f"[yellow]Warning: Skipping record {i+1} - missing 'page_content' field[/yellow]")
                        continue

                    if "embedding" not in data or not data["embedding"]:
                        console.print(f"[yellow]Warning: Skipping record {i+1} - missing 'embedding' field[/yellow]")
                        continue

                    # Prepare metadata
                    metadata = data.get("metadata", {})
                    if not metadata:
                        metadata = {}

                    # Insert data
                    cursor.execute(
                        f"INSERT INTO {table_name} (page_content, metadata, embedding) VALUES (?, ?, ?)",
                        (data["page_content"], json_dumps(metadata), str(data["embedding"])),
                    )
                    inserted_count += 1

                    progress = (i + 1) / total_lines * 100
                    console.print(f"Progress: {progress:.1f}% ({i+1}/{total_lines})", end="\r")

                except Exception as e:
                    console.print(f"[yellow]Warning: Error processing record {i+1}: {str(e)}[/yellow]")
                    continue

        console.print("\n[bold green]✅ Data loading completed successfully[/bold green]")
        console.print(f"[green]Inserted {inserted_count} of {total_lines} records into table '{table_name}'[/green]")


@app.command()
def similarity_search(
    db_path: Path = typer.Argument(Path("db.sqlite3"), help="Path to the SQLite database"),
    table_name: str = typer.Argument(None, help="Name of the table to query"),
    query: str = typer.Option(..., help="Text to search for similar documents"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL, help="Embedding model to use"
    ),
    limit: int = typer.Option(4, help="Maximum number of results to return"),
    no_metadata: bool = typer.Option(False, help="Hide metadata in the results"),
    debug: bool = typer.Option(False, help="Print SQL statements being executed"),
    verbose: bool = typer.Option(False, help="Print additional debug information"),
):
    """
    Perform a semantic similarity search in a SQLite vector database.

    This command:
    1. Connects to the specified SQLite database
    2. Loads the sqlite_vec extension
    3. Determines the embedding dimensions from the existing data
    4. Creates embeddings for the query text using the specified model
    5. Performs a vector similarity search against the database
    6. Returns the most similar documents ordered by distance

    The results include document ID, content, metadata, and distance score.
    """
    with get_db_cursor(db_path, debug=debug) as cursor:
        # Auto-detect table if not provided
        if table_name is None:
            table_name = detect_embedding_table(cursor)
            if verbose:
                console.print(f"[green]Using auto-detected table: '{table_name}'[/green]")

        current_dimensions = detect_embedding_dimensions(cursor, table_name)

        llm = LLM.create(embedding_model.value)

        if current_dimensions == llm.get_embed_size():
            if verbose:
                console.print(
                    f"[green]Matched Embedding dimensions : {current_dimensions} dimensions. Using {llm.embedding_model} for query embedding[/green]"
                )
        else:
            console.print("[bold red]Embedding dimensions mismatch![/bold red]")
            console.print(f"Current dimensions: {current_dimensions}")
            console.print(f"LLM dimensions: {llm.get_embed_size()}")
            raise typer.Exit(code=1)

        query_embedding = llm.embed(query)

        sql = f"""
            SELECT page_content, metadata, distance FROM {table_name}
            WHERE embedding MATCH vec_f32(?)
            ORDER BY distance
            LIMIT {limit}
        """
        cursor.execute(sql, (str(query_embedding),))
        results = cursor.fetchall()

        for i, (page_content, metadata, distance) in enumerate(results):
            if isinstance(metadata, str):
                try:
                    metadata = json_loads(metadata)
                    if isinstance(metadata, dict):
                        metadata.update({"distance": distance})
                except JSONDecodeError:
                    pass
            if not no_metadata:
                console.print(f"metadata: {metadata}\n")
            console.print(page_content.strip())
            if i < len(results) - 1:
                console.print("\n----\n")


def detect_embedding_table(cursor: sqlite3.Cursor) -> str:
    """Detect table with embedding column"""

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%embedding%'")
    tables = cursor.fetchall()

    if not tables:
        raise SQLiteVecError("No tables with embedding column found in the database")

    if len(tables) > 1:
        table_list = ", ".join([t[0] for t in tables])
        raise SQLiteVecError(
            f"Multiple tables with embedding column found: {table_list}\n" "Please specify a table name explicitly"
        )

    return tables[0][0]


def detect_embedding_dimensions(cursor: sqlite3.Cursor, table_name: str) -> int:
    """
    Detect the dimensions of embeddings in the specified table.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table containing embeddings

    Returns:
        The number of dimensions in the embeddings

    Raises:
        SQLiteVecError: If no embeddings are found or if there's an issue with the data
        typer.Exit: If no records with embeddings are found
    """
    try:
        # Get a sample record to determine embedding dimensions
        cursor.execute(f"SELECT vec_to_json(embedding) FROM {table_name} LIMIT 1")
        sample_row = cursor.fetchone()

        if not sample_row or not sample_row[0]:
            console.print(f"[yellow]Warning: No records with embeddings found in table '{table_name}'[/yellow]")
            raise typer.Exit(1)

        json_string: str = sample_row[0]
        embedding: list[float] = json_loads(json_string)
        current_dimensions = len(embedding)

        return current_dimensions
    except sqlite3.Error as e:
        raise SQLiteVecError(f"Error detecting embedding dimensions: {e}")
