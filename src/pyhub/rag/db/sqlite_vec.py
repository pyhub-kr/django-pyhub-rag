import contextlib
import dataclasses
import logging
import sqlite3
from enum import Enum
from pathlib import Path
from typing import Generator, Optional, Union

from pyhub.llm import LLM, LLMEmbeddingModelEnum
from pyhub.llm.types import Embed, EmbeddingDimensionsEnum

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

from pyhub.rag.json import JSONDecodeError, json_dumps, json_loads

logger = logging.getLogger(__name__)


class SQLiteVecError(Exception):
    """Base exception class for SQLite-vec related errors"""

    pass


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    L1 = "L1"
    L2 = "L2"


@dataclasses.dataclass
class Document:
    page_content: str
    metadata: dict
    id: Optional[int] = None


def load_extensions(conn: sqlite3.Connection):
    """Load sqlite_vec extension to the SQLite connection"""

    if sqlite_vec is None:
        raise SQLiteVecError(
            "Please install sqlite-vec library. Or check if you're using the correct virtual environment."
        )

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


@contextlib.contextmanager
def get_db_cursor(db_path: Path) -> Generator[sqlite3.Cursor, None, None]:
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

        def sql_trace_callback(sql):
            logger.debug(f"Executing: {sql}")

        conn.set_trace_callback(sql_trace_callback)

        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()


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
            raise SQLiteVecError(f"No records with embeddings found in '{table_name}' table.")

        json_string: str = sample_row[0]
        embedding: list[float] = json_loads(json_string)
        current_dimensions = len(embedding)

        return current_dimensions
    except sqlite3.Error as e:
        raise SQLiteVecError(f"Error detecting embedding dimensions: {e}")


def create_virtual_table(
    db_path: Path,
    table_name: str,
    dimensions: EmbeddingDimensionsEnum,
    distance_metric: DistanceMetric,
):
    sql = f"""
CREATE VIRTUAL TABLE {table_name} using vec0(
    id integer PRIMARY KEY AUTOINCREMENT, 
    page_content text NOT NULL, 
    metadata text NOT NULL CHECK ((JSON_VALID(metadata) OR metadata IS NULL)), 
    embedding float[{dimensions.value}] distance_metric={distance_metric.value}
)
    """

    with get_db_cursor(db_path) as cursor:
        logger.debug(f"Executing: {sql}")

        try:
            cursor.execute(sql)
        except sqlite3.OperationalError as e:
            raise SQLiteVecError(f"Error: {e}")


def import_jsonl(
    db_path: Path,
    table_name: Optional[str],
    jsonl_path: Path,
    clear: bool,
):
    with get_db_cursor(db_path) as cursor:
        # Auto-detect table with embedding column if table_name is not provided
        if table_name is None:
            table_name = detect_embedding_table(cursor)
            logger.info(f"Auto-detected table: '{table_name}'")

        # Clear existing data if requested
        if clear:
            try:
                cursor.execute(f"DELETE FROM {table_name}")
                deleted_count = cursor.rowcount
                logger.warning(f"Cleared {deleted_count} existing records from table '{table_name}'")
            except sqlite3.Error as e:
                raise SQLiteVecError(f"Error clearing table: {str(e)}")

        # Read and insert data from JSONL
        with jsonl_path.open("r", encoding="utf-8") as f:
            total_lines = sum(1 for __ in f)
            f.seek(0)

            logger.info(f"Found {total_lines} records in JSONL file")

            inserted_count = 0
            for i, line in enumerate(f):
                try:
                    data = json_loads(line.strip())

                    # Check required fields
                    if "page_content" not in data:
                        logger.warning(f"Skipping record {i+1} - missing 'page_content' field")
                        continue

                    if "embedding" not in data or not data["embedding"]:
                        logger.warning(f"Skipping record {i+1} - missing 'embedding' field")
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
                    logger.debug(f"Progress: {progress:.1f}% ({i+1}/{total_lines})")

                except Exception as e:
                    logger.warning(f"Error processing record {i+1}: {str(e)}")
                    continue

        logger.info("✅ Data loading completed successfully")
        logger.info(f"Inserted {inserted_count} of {total_lines} records into table '{table_name}'")


def similarity_search(
    db_path: Path,
    table_name: Optional[str],
    query: Optional[str] = None,
    query_embedding: Optional[Union[list[float], Embed]] = None,
    embedding_model: LLMEmbeddingModelEnum = LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
    api_key: Optional[str] = None,
    limit: int = 4,
) -> list[Document]:
    with get_db_cursor(db_path) as cursor:
        # Auto-detect table if not provided
        if table_name is None:
            table_name = detect_embedding_table(cursor)
            logger.info(f"Using auto-detected table: '{table_name}'")

        if query is None and query_embedding is None:
            raise SQLiteVecError("Either query or query_embedding must be specified")

        if query_embedding is None:
            current_dimensions = detect_embedding_dimensions(cursor, table_name)

            if isinstance(embedding_model, Enum):
                embedding_model = embedding_model.value

            llm = LLM.create(embedding_model, api_key=api_key)
            if current_dimensions == llm.embed_size:
                logger.info(
                    f"Matched Embedding dimensions : {current_dimensions} dimensions. Using {llm.embedding_model} for query embedding"
                )
            else:
                raise SQLiteVecError(
                    f"Embedding dimensions mismatch! (llm = {llm.embedding_model}, db = {current_dimensions})"
                )

            query_embedding = llm.embed(query)

        sql = f"""
            SELECT page_content, metadata, distance FROM {table_name}
            WHERE embedding MATCH vec_f32(?)
            ORDER BY distance
            LIMIT {limit}
        """
        cursor.execute(sql, (str(query_embedding),))
        results = cursor.fetchall()

        document_list = []
        for page_content, metadata, distance in results:
            if isinstance(metadata, str):
                try:
                    metadata = json_loads(metadata)
                    if isinstance(metadata, dict):
                        metadata.update({"distance": distance})
                except JSONDecodeError:
                    pass

            document = Document(
                page_content=page_content,
                metadata=metadata,
            )
            document_list.append(document)

        return document_list
