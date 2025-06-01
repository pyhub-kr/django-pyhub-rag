"""Calculator tool implementation."""

import re

from pydantic import BaseModel, Field, field_validator

from ..base import BaseTool, ValidationLevel


class CalculatorInput(BaseModel):
    """Calculator 도구의 입력 스키마"""

    expression: str = Field(..., description="수식 (예: '2 + 2', '10 * 5')")

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v: str) -> str:
        """수식 검증"""
        # 기본 검증
        if not v or not v.strip():
            raise ValueError("Expression cannot be empty")

        # 길이 제한
        if len(v) > 100:
            raise ValueError("Expression is too long (max 100 characters)")

        # 허용된 문자만 포함하는지 확인
        if not re.match(r"^[\d\s+\-*/().,]+$", v):
            raise ValueError("Expression contains invalid characters")

        # 불완전한 수식 검사
        v_stripped = v.strip()
        if v_stripped.endswith(("+", "-", "*", "/", "(")):
            raise ValueError("Expression is incomplete")
        if v_stripped.startswith((")", "*", "/")):
            raise ValueError("Expression has invalid start")

        # 큰 지수 연산 방지
        if "**" in v:
            parts = v.split("**")
            for i in range(1, len(parts)):
                # 지수 부분 추출 및 검증
                exp_match = re.match(r"^\s*(\d+)", parts[i])
                if exp_match:
                    exp_value = int(exp_match.group(1))
                    if exp_value > 100:
                        raise ValueError("Exponent too large (max 100)")

        # 위험한 패턴 검출
        dangerous_patterns = [
            r"__",  # 던더 메서드
            r"import",  # 임포트 시도
            r"exec",  # 실행 시도
            r"eval",  # eval 중첩
            r"open",  # 파일 열기
            r"file",  # 파일 접근
            r"input",  # 입력 시도
            r"print",  # 출력 시도
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Expression contains forbidden pattern: {pattern}")

        return v


class Calculator(BaseTool):
    """수학 계산을 수행하는 도구"""

    def __init__(self):
        super().__init__(name="calculator", description="Performs mathematical calculations")
        self.args_schema = CalculatorInput
        self.validation_level = ValidationLevel.STRICT

    def run(self, expression: str) -> str:
        """계산 실행"""
        try:
            # 안전한 수식 평가
            # eval을 사용하지만 입력 검증으로 안전성 확보
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Calculation error: {str(e)}"
