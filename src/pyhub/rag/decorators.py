import warnings
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


def warn_if_async(func: T) -> T:
    """비동기 컨텍스트에서 호출되면 경고를 발생시키는 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        import asyncio

        try:
            if asyncio.get_running_loop():
                warnings.warn(
                    f"비동기 컨텍스트에서 동기 메서드 {func.__name__}이(가) 호출되었습니다. "
                    f"대신 비동기 메서드 a{func.__name__}을(를) 권장드립니다.",
                    RuntimeWarning,
                    stacklevel=2,
                )
        except RuntimeError:
            # 비동기 컨텍스트가 아닌 경우 무시
            pass
        return func(*args, **kwargs)

    return wrapper
