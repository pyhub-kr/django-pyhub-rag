"""재시도 및 에러 처리 유틸리티"""

import random
import time
from functools import wraps
from typing import Any, Callable, Type

from rich.console import Console

console = Console()


class RetryError(Exception):
    """재시도 실패 시 발생하는 예외"""

    pass


def exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None,
    verbose: bool = False,
):
    """지수 백오프를 사용한 재시도 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        initial_delay: 초기 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        exponential_base: 지수 증가 베이스
        jitter: 지터 추가 여부 (대기 시간에 랜덤성 추가)
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 함수
        verbose: 상세 로그 출력 여부
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        # 마지막 시도였으면 예외 발생
                        raise RetryError(f"최대 재시도 횟수 {max_retries}회 초과") from e

                    # 대기 시간 계산
                    delay = min(initial_delay * (exponential_base**attempt), max_delay)

                    # 지터 추가
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    # 재시도 콜백 호출
                    if on_retry:
                        on_retry(e, attempt + 1)

                    # 로그 출력
                    if verbose:
                        console.print(
                            f"[yellow]재시도 {attempt + 1}/{max_retries}: "
                            f"{type(e).__name__}: {str(e)} "
                            f"({delay:.1f}초 대기)[/yellow]"
                        )

                    # 대기
                    time.sleep(delay)

            # 여기에 도달하면 안 됨
            raise last_exception

        return wrapper

    return decorator


def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable = None,
    max_retries: int = 2,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    verbose: bool = False,
) -> Any:
    """기본 함수 실패 시 대체 함수를 시도하는 재시도 패턴

    Args:
        primary_func: 기본 함수
        fallback_func: 대체 함수
        max_retries: 각 함수의 최대 재시도 횟수
        exceptions: 재시도할 예외 타입들
        verbose: 상세 로그 출력 여부
    """
    # 기본 함수 시도
    try:

        @exponential_backoff(
            max_retries=max_retries,
            exceptions=exceptions,
            verbose=verbose,
        )
        def try_primary():
            return primary_func()

        return try_primary()

    except (RetryError, *exceptions) as e:
        if verbose:
            console.print(f"[yellow]기본 함수 실패: {e}[/yellow]")

        # 대체 함수가 있으면 시도
        if fallback_func:
            if verbose:
                console.print("[blue]대체 함수 시도 중...[/blue]")

            try:

                @exponential_backoff(
                    max_retries=max_retries,
                    exceptions=exceptions,
                    verbose=verbose,
                )
                def try_fallback():
                    return fallback_func()

                return try_fallback()

            except (RetryError, *exceptions) as fallback_e:
                if verbose:
                    console.print(f"[red]대체 함수도 실패: {fallback_e}[/red]")
                raise
        else:
            raise


# API 에러 처리를 위한 특화된 데코레이터
def retry_api_call(
    max_retries: int = 3,
    rate_limit_retries: int = 5,
    network_error_retries: int = 3,
    verbose: bool = False,
):
    """API 호출에 특화된 재시도 데코레이터

    다음 에러들을 구분하여 처리:
    - Rate limit 에러: 더 긴 대기 시간과 더 많은 재시도
    - 네트워크 에러: 표준 재시도
    - 인증 에러: 재시도하지 않음
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 에러 타입별 재시도 설정
            error_configs = [
                # Rate limit 에러
                {
                    "exceptions": (RateLimitError,),
                    "max_retries": rate_limit_retries,
                    "initial_delay": 5.0,
                    "max_delay": 300.0,  # 5분
                    "message": "API 요청 제한 도달",
                },
                # 네트워크 에러
                {
                    "exceptions": (NetworkError, TimeoutError),
                    "max_retries": network_error_retries,
                    "initial_delay": 1.0,
                    "max_delay": 30.0,
                    "message": "네트워크 오류",
                },
                # 서버 에러
                {
                    "exceptions": (ServerError,),
                    "max_retries": max_retries,
                    "initial_delay": 2.0,
                    "max_delay": 60.0,
                    "message": "서버 오류",
                },
            ]

            last_exception = None

            for config in error_configs:
                try:

                    @exponential_backoff(
                        max_retries=config["max_retries"],
                        initial_delay=config["initial_delay"],
                        max_delay=config["max_delay"],
                        exceptions=config["exceptions"],
                        verbose=verbose,
                        on_retry=lambda e, attempt: (
                            console.print(
                                f"[yellow]{config['message']}: {e} "
                                f"(재시도 {attempt}/{config['max_retries']})[/yellow]"
                            )
                            if verbose
                            else None
                        ),
                    )
                    def try_call():
                        return func(*args, **kwargs)

                    return try_call()

                except config["exceptions"] as e:
                    last_exception = e
                    continue
                except Exception:
                    # 다른 예외는 바로 전파
                    raise

            # 모든 재시도 실패
            if last_exception:
                raise last_exception
            else:
                # 일반 호출 시도
                return func(*args, **kwargs)

        return wrapper

    return decorator


# 커스텀 예외 클래스들
class APIError(Exception):
    """API 관련 기본 예외"""

    pass


class RateLimitError(APIError):
    """API 요청 제한 초과"""

    pass


class NetworkError(APIError):
    """네트워크 연결 오류"""

    pass


class ServerError(APIError):
    """서버 오류 (5xx)"""

    pass


class AuthenticationError(APIError):
    """인증 오류 (재시도하면 안 됨)"""

    pass


def handle_api_error(e: Exception) -> None:
    """API 에러를 적절한 예외 타입으로 변환"""
    error_message = str(e).lower()

    # Rate limit 에러 패턴
    if any(pattern in error_message for pattern in ["rate limit", "too many requests", "429", "quota exceeded"]):
        raise RateLimitError(str(e)) from e

    # 네트워크 에러 패턴
    elif any(pattern in error_message for pattern in ["connection", "timeout", "network", "dns", "refused"]):
        raise NetworkError(str(e)) from e

    # 서버 에러 패턴
    elif any(pattern in error_message for pattern in ["500", "502", "503", "504", "server error", "internal error"]):
        raise ServerError(str(e)) from e

    # 인증 에러 패턴
    elif any(
        pattern in error_message for pattern in ["401", "403", "unauthorized", "forbidden", "api key", "authentication"]
    ):
        raise AuthenticationError(str(e)) from e

    # 기타 에러는 그대로 전파
    else:
        raise
