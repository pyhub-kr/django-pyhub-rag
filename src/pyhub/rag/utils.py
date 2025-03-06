import sqlite3
from functools import lru_cache
from logging import getLogger
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Generator,
    Iterable,
    List,
    Literal,
    Set,
    Tuple,
    Union,
    get_args,
    get_origin,
)

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


@lru_cache(maxsize=32)
def get_literal_values(*type_hints: Any) -> Set[Any]:
    """
    중첩된 타입 구조(Union, Literal 등)에서 모든 리터럴 값을 추출하는 함수

    Args:
        *type_hints: 타입 힌트들 (Union, Literal 등 중첩 가능)

    Returns:
        모든 리터럴 값의 집합
    """
    values = set()

    for type_hint in type_hints:
        # None인 경우 다음 타입으로 진행
        if type_hint is None:
            continue

        # type(None)인 경우 None 값 추가
        if type_hint is type(None):
            values.add(None)
            continue

        # 타입 객체가 아닌 실제 값인 경우 그대로 추가
        if not isinstance(type_hint, type) and not hasattr(type_hint, "__origin__"):
            values.add(type_hint)
            continue

        # 타입의 origin 확인 (Union, Literal 등)
        origin = get_origin(type_hint)

        # Literal 타입인 경우
        if origin is Literal:
            values.update(get_args(type_hint))

        # Union 타입인 경우 (typing.Union 또는 | 연산자)
        elif origin is Union:
            for arg in get_args(type_hint):
                values.update(get_literal_values(arg))

        # 그 외 복합 타입인 경우
        elif origin is not None:
            for arg in get_args(type_hint):
                values.update(get_literal_values(arg))

    return values
