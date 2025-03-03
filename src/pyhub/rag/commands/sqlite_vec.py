import os
import sqlite3
from enum import Enum

import sqlite_vec
import typer
from rich.console import Console

console = Console()


class Dimensions(str, Enum):
    TEXT_EMBEDDING_3_SMALL = "1536"
    TEXT_EMBEDDING_3_LARGE = "3072"
    TEXT_EMBEDDING_004 = "3072"


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    L1 = "L1"
    L2 = "L2"


def load_extensions(conn: sqlite3.Connection):
    """Load sqlite_vec extension to the SQLite connection"""
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def create_sqlite_vec_table(
    db_path: str = typer.Argument(..., help="sqlite db path"),
    table_name: str = typer.Argument(..., help="table name"),
    dimensions: Dimensions = Dimensions.TEXT_EMBEDDING_3_SMALL,
    distance_metric: DistanceMetric = DistanceMetric.COSINE,
):
    """Create a vector table using sqlite-vec extension in SQLite database"""

    db_path = os.path.abspath(db_path)

    extension = os.path.splitext(db_path)[-1]
    if not extension:
        db_path = f"{db_path}.sqlite3"
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
