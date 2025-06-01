"""
LLM 모듈 설정 관리
"""

import os


class LLMSettings:
    """LLM 모듈의 설정을 관리하는 클래스"""

    def __init__(self):
        # Trace 관련 설정
        self.trace_enabled = self._parse_bool("PYHUB_LLM_TRACE", False)
        self.trace_function_calls = self._parse_bool("PYHUB_LLM_TRACE_FUNCTION_CALLS", False)
        self.trace_level = os.getenv("PYHUB_LLM_TRACE_LEVEL", "INFO").upper()

    def _parse_bool(self, env_var: str, default: bool) -> bool:
        """환경변수를 bool 값으로 파싱"""
        value = os.getenv(env_var, str(default)).lower()
        return value in ("true", "1", "yes", "on")


# 전역 인스턴스
llm_settings = LLMSettings()


__all__ = ["LLMSettings", "llm_settings"]
