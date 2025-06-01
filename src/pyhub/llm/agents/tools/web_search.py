"""Web search tool implementation."""

from ..base import BaseTool, ValidationLevel
from .schemas import WebSearchInput


class WebSearch(BaseTool):
    """웹 검색을 수행하는 도구"""

    def __init__(self):
        super().__init__(name="web_search", description="Search the web for information")
        self.args_schema = WebSearchInput
        self.validation_level = ValidationLevel.WARNING

    def run(self, query: str, max_results: int = 5) -> str:
        """웹 검색 실행 (예제 구현)"""
        # 실제 구현에서는 검색 API를 호출
        return f"Found {max_results} results for '{query}': [Result 1], [Result 2], ..."
