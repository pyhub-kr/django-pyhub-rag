"""File reader tool implementation."""

import os

from pydantic import BaseModel, Field

from ..base import BaseTool, ValidationLevel


class FileReaderInput(BaseModel):
    """파일 읽기 도구의 입력 스키마"""

    path: str = Field(..., description="읽을 파일의 경로")
    encoding: str = Field("utf-8", description="파일 인코딩")


class FileReader(BaseTool):
    """파일을 읽는 도구"""

    def __init__(self):
        super().__init__(name="file_reader", description="Read contents of a text file")
        self.args_schema = FileReaderInput
        self.validation_level = ValidationLevel.STRICT

    def run(self, path: str, encoding: str = "utf-8") -> str:
        """파일 읽기 실행"""
        try:
            # 보안을 위해 상대 경로만 허용
            if os.path.isabs(path):
                return "Error: Only relative paths are allowed"

            # 상위 디렉토리 접근 차단
            if ".." in path:
                return "Error: Parent directory access is not allowed"

            # 파일 읽기
            with open(path, "r", encoding=encoding) as f:
                content = f.read()

            # 내용이 너무 길면 잘라서 반환
            if len(content) > 1000:
                return content[:1000] + "\n... (truncated)"

            return content

        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
