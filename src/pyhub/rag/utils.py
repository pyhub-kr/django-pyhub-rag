import sqlite3
from logging import getLogger
from typing import Any, AsyncIterator, Callable, Generator, Iterable, List, Tuple

logger = getLogger(__name__)


async def aenumerate(iterable: AsyncIterator[Any], start=0) -> AsyncIterator[Tuple[str, Any]]:
    """Async version of enumerate function."""

    i = start
    async for x in iterable:
        yield i, x
        i += 1


def make_groups_by_length(
    text_list: Iterable[str],
    group_max_length: int,
    length_func: Callable[[str], int] = len,
) -> Generator[List[str], None, None]:
    batch, group_length = [], 0
    for text in text_list:
        text_length = length_func(text)
        if group_length + text_length >= group_max_length:
            msg = "Made group : length=%d, item size=%d"
            logger.debug(msg, group_length, len(batch))
            yield batch  # 현재 배치 반환
            batch, group_length = [], 0
        batch.append(text)
        group_length += text_length
    if batch:
        msg = "Made group : length=%d, item size=%d"
        logger.debug(msg, group_length, len(batch))
        yield batch  # 마지막 배치 반환


def load_sqlite_vec_extension(connection: sqlite3.Connection):
    import sqlite_vec

    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)

    logger.debug("sqlite-vec extension loaded")
