import sqlite3
import sys
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

from pyhub.llm import LLM
from pyhub.llm.enum import EmbeddingDimensionsEnum, LLMEmbeddingModelEnum
from pyhub.rag.json import json_dumps, json_loads

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
            "[bold red]❌ ARM version of Python does not support sqlite-vec library. Please reinstall AMD64 version of Python.[/bold red]"
        )
        raise typer.Exit(code=1)

    if not is_python_3_10_or_later:
        console.print("[bold red]❌ Python 3.10 or later is required.[/bold red]")
        raise typer.Exit(code=1)

    if sqlite_vec is None:
        console.print("[bold red]❌ Please install sqlite-vec library.[/bold red]")
        raise typer.Exit(code=1)

    with sqlite3.connect(":memory:") as db:
        try:
            load_extensions(db)
        except AttributeError:
            console.print(
                "[bold red]❌ This Python does not support sqlite3 extension. Please refer to the guide and reinstall Python.[/bold red]"
            )
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]✅ This Python supports sqlite3 extension.[/bold green]")
            console.print("[bold green]✅ sqlite-vec extension is working properly.[/bold green]")


@app.command()
def create_table(
    db_path: Path = typer.Argument(..., help="sqlite db path"),
    table_name: str = typer.Argument(..., help="table name"),
    dimensions: EmbeddingDimensionsEnum = EmbeddingDimensionsEnum.D_1536,
    distance_metric: DistanceMetric = DistanceMetric.COSINE,
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

    with sqlite3.connect(db_path) as conn:
        load_extensions(conn)

        cursor = conn.cursor()

        # Print the SQL query for informational purposes
        console.print("[blue]Executing SQL:[/blue]")
        console.print(f"[cyan]{sql}[/cyan]")

        try:
            cursor.execute(sql)
        except sqlite3.OperationalError as e:
            console.print(f"[red]{e} (db_path: {db_path}[/red]")
            raise typer.Exit(code=1)

        conn.commit()
        console.print(f"[bold green]Successfully created virtual table '{table_name}' in {db_path}[/bold green]")


@app.command()
def import_jsonl(
    db_path: Path = typer.Argument(..., help="sqlite db path"),
    table_name: str = typer.Argument(..., help="table name"),
    jsonl_path: Path = typer.Argument(..., help="Path to the JSONL file with embeddings"),
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
    """

    with sqlite3.connect(db_path) as conn:
        load_extensions(conn)

        # Set up SQL tracing callback to print executed SQL statements if debug is enabled
        if debug:

            def sql_trace_callback(sql):
                console.print(f"[dim blue]Executing: {sql}[/dim blue]")

            conn.set_trace_callback(sql_trace_callback)

        cursor = conn.cursor()

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

        conn.commit()
        console.print("\n[bold green]✅ Data loading completed successfully[/bold green]")
        console.print(f"[green]Inserted {inserted_count} of {total_lines} records into table '{table_name}'[/green]")


@app.command()
def similarity_search(
    db_path: Path = typer.Argument(..., help="Path to the SQLite database"),
    table_name: str = typer.Argument(..., help="Name of the table to query"),
    embedding_model: LLMEmbeddingModelEnum = LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
    query: str = typer.Argument(..., help="Text to search for similar documents"),
    limit: int = typer.Option(4, help="Maximum number of results to return"),
    debug: bool = typer.Option(False, help="Print SQL statements being executed"),
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
    with sqlite3.connect(db_path) as conn:
        load_extensions(conn)

        # Set up SQL tracing callback to print executed SQL statements if debug is enabled
        if debug:

            def sql_trace_callback(sql):
                console.print(f"[dim blue]Executing: {sql}[/dim blue]")

            conn.set_trace_callback(sql_trace_callback)

        cursor = conn.cursor()

        # Get a sample record to determine embedding dimensions
        cursor.execute(f"SELECT vec_to_json(embedding) FROM {table_name} LIMIT 1")
        sample_row = cursor.fetchone()

        if not sample_row or not sample_row[0]:
            console.print(f"[yellow]Warning: No records with embeddings found in table '{table_name}'[/yellow]")
            raise typer.Exit(1)

        json_string: str = sample_row[0]
        embedding: list[float] = json_loads(json_string)
        current_dimensions = len(embedding)
        console.print(f"Embedding dimensions: {current_dimensions}")

        llm = LLM.create(embedding_model.value)
        console.print(f"Using {llm.embedding_model} (dimensions: {llm.get_embed_size()})")

        if current_dimensions != llm.get_embed_size():
            console.print("[bold red]Embedding dimensions mismatch![/bold red]")
            console.print(f"Current dimensions: {current_dimensions}")
            console.print(f"LLM dimensions: {llm.get_embed_size()}")
            raise typer.Exit(code=1)

        query_embedding = llm.embed(query)

        sql = f"""
            SELECT id, page_content, metadata, distance FROM {table_name}
            WHERE embedding MATCH vec_f32(?)
            ORDER BY distance
            LIMIT {limit}
        """
        cursor.execute(sql, (str(query_embedding),))
        results = cursor.fetchall()

        for _id, page_content, metadata, distance in results:
            console.print()
            console.print(f"[bold reverse]문서 #{_id} (distance: {distance})[/bold reverse]")
            console.print(page_content)
            console.print("metadata :", metadata)
            console.print()
