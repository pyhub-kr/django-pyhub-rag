"""LLM 관련 믹스인 클래스들"""

from functools import wraps
from typing import Callable

from rich.console import Console

from .retry import (
    AuthenticationError,
    handle_api_error,
    retry_api_call,
)

console = Console()


class RetryMixin:
    """API 호출에 재시도 로직을 추가하는 믹스인"""

    def __init__(self, *args, enable_retry: bool = True, retry_verbose: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_retry = enable_retry
        self.retry_verbose = retry_verbose

    def _wrap_with_retry(self, func: Callable) -> Callable:
        """함수에 재시도 로직을 래핑"""
        if not self.enable_retry:
            return func

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # API 에러를 적절한 타입으로 변환
                try:
                    handle_api_error(e)
                except AuthenticationError:
                    # 인증 에러는 재시도하지 않음
                    console.print(f"[red]인증 오류: {e}[/red]")
                    console.print("[yellow]API 키를 확인해주세요.[/yellow]")
                    raise
                except Exception:
                    # 변환된 에러로 재시도
                    @retry_api_call(verbose=self.retry_verbose)
                    def retry_func():
                        return func(*args, **kwargs)

                    return retry_func()

        return wrapper

    def ask(self, *args, **kwargs):
        """ask 메서드에 재시도 로직 적용"""
        original_ask = super().ask
        wrapped_ask = self._wrap_with_retry(original_ask)
        return wrapped_ask(*args, **kwargs)

    def ask_async(self, *args, **kwargs):
        """ask_async 메서드에 재시도 로직 적용"""
        original_ask_async = super().ask_async

        async def async_wrapper(*args, **kwargs):
            try:
                return await original_ask_async(*args, **kwargs)
            except Exception as e:
                # 비동기 버전도 동일하게 처리
                try:
                    handle_api_error(e)
                except AuthenticationError:
                    console.print(f"[red]인증 오류: {e}[/red]")
                    console.print("[yellow]API 키를 확인해주세요.[/yellow]")
                    raise
                except Exception:
                    # 간단한 재시도 (비동기 데코레이터는 복잡하므로 간단히 구현)
                    import asyncio

                    for attempt in range(3):
                        try:
                            await asyncio.sleep(2**attempt)
                            return await original_ask_async(*args, **kwargs)
                        except Exception as retry_e:
                            if attempt == 2:
                                raise retry_e

        return async_wrapper(*args, **kwargs)

    def embed(self, *args, **kwargs):
        """embed 메서드에 재시도 로직 적용"""
        original_embed = super().embed
        wrapped_embed = self._wrap_with_retry(original_embed)
        return wrapped_embed(*args, **kwargs)


class ValidationMixin:
    """입력 검증을 추가하는 믹스인"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 모델별 토큰 제한 (대략적인 값)
        self.model_token_limits = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "claude-3-5-sonnet-latest": 200000,
            "claude-3-5-haiku-latest": 200000,
            "gemini-1.5-pro": 1000000,
            "gemini-1.5-flash": 1000000,
        }

    def _validate_token_limit(self, text: str, max_tokens: int = None) -> None:
        """토큰 제한 검증"""
        # 간단한 토큰 추정 (실제로는 tokenizer 사용해야 함)
        estimated_tokens = len(text) // 4  # 대략 4글자당 1토큰

        if max_tokens:
            estimated_total = estimated_tokens + max_tokens
        else:
            estimated_total = estimated_tokens + getattr(self, "max_tokens", 1000)

        model = getattr(self, "model", "")
        limit = self.model_token_limits.get(model, 128000)

        if estimated_total > limit:
            console.print(
                f"[yellow]경고: 예상 토큰 수({estimated_total})가 " f"모델 제한({limit})에 근접합니다.[/yellow]"
            )

    def ask(self, query: str, *args, **kwargs):
        """ask 메서드에 검증 추가"""
        self._validate_token_limit(query, kwargs.get("max_tokens"))
        return super().ask(query, *args, **kwargs)

    def embed(self, text: str, *args, **kwargs):
        """embed 메서드에 검증 추가"""
        # 임베딩은 보통 8191 토큰 제한
        if len(text) // 4 > 8191:
            console.print("[yellow]경고: 텍스트가 임베딩 토큰 제한(8191)을 " "초과할 수 있습니다.[/yellow]")
        return super().embed(text, *args, **kwargs)
