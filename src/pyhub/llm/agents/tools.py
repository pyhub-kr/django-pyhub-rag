"""Built-in tools for agents."""

import os
import re
from typing import Optional

from pydantic import BaseModel, Field, validator

from .base import BaseTool, AsyncBaseTool


class CalculatorInput(BaseModel):
    """계산기 입력 스키마"""
    expression: str = Field(..., description="수학 표현식")
    
    @validator('expression')
    def validate_expression(cls, v):
        """수식 유효성 검증"""
        # 허용된 문자만 포함하는지 확인
        allowed_pattern = r'^[\d\+\-\*/\(\)\.\s]+$'
        if not re.match(allowed_pattern, v):
            raise ValueError("Expression contains invalid characters")
        
        # 위험한 패턴 검사
        dangerous_patterns = [
            r'__',  # 더블 언더스코어 (매직 메서드)
            r'import',  # 임포트 문
            r'eval',  # eval 함수
            r'exec',  # exec 함수
            r'compile',  # compile 함수
            r'globals',  # globals 함수
            r'locals',  # locals 함수
            r'\*\*\s*\d{4,}',  # 너무 큰 지수
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Expression contains forbidden pattern: {pattern}")
        
        # 기본적인 수식 구조 검증
        try:
            compile(v, '<string>', 'eval')
        except SyntaxError:
            raise ValueError("Invalid expression syntax")
        
        # 균형 잡힌 괄호 확인
        if v.count('(') != v.count(')'):
            raise ValueError("Unbalanced parentheses")
        
        return v


class Calculator(BaseTool):
    """계산기 도구"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Performs basic mathematical calculations. Input should be a valid mathematical expression.",
            args_schema=CalculatorInput
        )
    
    def run(self, expression: str) -> str:
        """수식을 계산합니다."""
        try:
            # 입력 검증
            validated_input = CalculatorInput(expression=expression)
            
            # 안전한 환경에서 계산 수행
            # eval을 사용하지만 입력이 검증되었으므로 안전
            result = eval(validated_input.expression)
            
            # 결과 포맷팅
            if isinstance(result, float):
                # 소수점 자리수 제한
                if result == int(result):
                    return str(int(result))
                else:
                    return f"{result:.6f}".rstrip('0').rstrip('.')
            
            return str(result)
            
        except Exception as e:
            return f"Calculation error: {str(e)}"


class WebSearchInput(BaseModel):
    """웹 검색 입력 스키마"""
    query: str = Field(..., min_length=1, max_length=200, description="검색 쿼리")
    max_results: int = Field(default=5, ge=1, le=20, description="최대 결과 수")
    language: str = Field(default="ko", pattern="^[a-z]{2}$", description="언어 코드")


class FileOperationInput(BaseModel):
    """파일 작업 입력 스키마"""
    path: str = Field(..., description="파일 경로")
    operation: str = Field(..., pattern="^(read|write|delete)$", description="작업 종류")
    content: Optional[str] = Field(None, description="쓸 내용 (write 작업시)")
    
    @validator('path')
    def validate_path(cls, v):
        """경로 보안 검증"""
        # 경로 탐색 공격 방지
        if '..' in v:
            raise ValueError("Path traversal not allowed")
        
        # 위험한 시스템 경로 차단
        dangerous_paths = ['/etc', '/sys', '/proc', '/dev', '/boot']
        abs_path = os.path.abspath(v)
        
        for dangerous in dangerous_paths:
            if abs_path.startswith(dangerous):
                raise ValueError(f"Access to {dangerous} is not allowed")
        
        return v
    
    @validator('content')
    def validate_content(cls, v, values):
        """내용 검증"""
        if values.get('operation') == 'write' and v is None:
            raise ValueError("Content is required for write operation")
        return v


# 추가 도구들은 필요에 따라 구현...