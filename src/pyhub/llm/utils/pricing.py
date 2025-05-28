"""LLM 모델별 가격 정보 및 비용 계산 유틸리티"""

# 모델별 가격 정보 (USD per 1M tokens)
# 2024년 기준
PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "chatgpt-4o-latest": {"input": 5.00, "output": 15.00},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    # Anthropic
    "claude-3-opus-latest": {"input": 15.00, "output": 75.00},
    "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-latest": {"input": 0.80, "output": 4.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    # Google
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-lite": {"input": 0.015, "output": 0.06},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Upstage
    "solar-pro": {"input": 3.00, "output": 10.00},
    "solar-mini": {"input": 0.30, "output": 0.90},
    # Embedding models
    "text-embedding-3-small": {"input": 0.020, "output": 0},
    "text-embedding-3-large": {"input": 0.130, "output": 0},
    "text-embedding-ada-002": {"input": 0.100, "output": 0},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    """모델과 토큰 수를 기반으로 비용 계산"""
    if model not in PRICING:
        # 알 수 없는 모델은 gpt-4o-mini 가격으로 추정
        pricing = PRICING["gpt-4o-mini"]
    else:
        pricing = PRICING[model]

    # 1M 토큰당 가격이므로 변환
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
