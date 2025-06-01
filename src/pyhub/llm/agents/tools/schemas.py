"""Common input schemas for tools."""

from pydantic import BaseModel, Field, field_validator


class WebSearchInput(BaseModel):
    """웹 검색 도구의 입력 스키마"""

    query: str = Field(..., description="검색어")
    max_results: int = Field(5, description="최대 결과 수", ge=1, le=100)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """검색어 검증"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")

        if len(v) > 500:
            raise ValueError("Query is too long (max 500 characters)")

        return v.strip()


class FileOperationInput(BaseModel):
    """파일 작업 도구의 입력 스키마"""

    path: str = Field(..., description="파일 경로")
    operation: str = Field(..., description="작업 유형", pattern=r"^(read|write|append|delete)$")
    content: str = Field(None, description="파일에 쓸 내용 (write/append 시)")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """경로 검증"""
        if not v:
            raise ValueError("Path cannot be empty")

        # 위험한 경로 패턴 차단
        dangerous_patterns = [
            "..",  # 상위 디렉토리 접근
            "~",  # 홈 디렉토리
            "/etc",  # 시스템 설정
            "/sys",  # 시스템 파일
            "/proc",  # 프로세스 정보
        ]

        for pattern in dangerous_patterns:
            if pattern in v:
                raise ValueError(f"Path contains forbidden pattern: {pattern}")

        return v
