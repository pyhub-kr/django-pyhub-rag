import os
import sqlite3
import sys
from enum import Enum

import typer
from rich.console import Console

from pyhub.llm.enum import EmbeddingDimensionsEnum

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

# SQLite-vec 서브 명령 그룹 생성
app = typer.Typer(name="sqlite-vec", help="SQLite-vec 관련 명령어")
console = Console()


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    L1 = "L1"
    L2 = "L2"


def load_extensions(conn: sqlite3.Connection):
    """Load sqlite_vec extension to the SQLite connection"""
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


@app.command(name="check")
def check():
    """Check if sqlite-vec extension can be loaded properly"""

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


@app.command(name="create-table")
def create_table(
    db_path: str = typer.Argument(..., help="sqlite db path"),
    table_name: str = typer.Argument(..., help="table name"),
    dimensions: EmbeddingDimensionsEnum = EmbeddingDimensionsEnum.D_1536,
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
