"""React Agent implementation."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ..base import BaseLLM
from .base import AsyncBaseAgent, BaseAgent, Tool, ToolExecutor
from .simple_template import SimpleTemplate

logger = logging.getLogger(__name__)

# Try to import Django components
DJANGO_AVAILABLE = False
get_template = None
DjangoTemplate = None
Context = None

try:
    from django.conf import settings

    if settings.configured:
        from django.template import Context
        from django.template.loader import get_template

        DJANGO_AVAILABLE = True
except Exception:
    pass


@dataclass
class ReactStep:
    """React 단계 정보"""

    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    final_answer: Optional[str] = None

    @property
    def is_final(self) -> bool:
        """최종 답변인지 확인"""
        return self.final_answer is not None


def parse_react_output(output: str) -> ReactStep:
    """LLM 출력을 ReactStep으로 파싱"""
    # 각 섹션을 추출하는 정규식
    thought_pattern = r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)"
    action_pattern = r"Action:\s*(.+?)(?=Action Input:|$)"
    action_input_pattern = r"Action Input:\s*(.+?)(?=Observation:|$)"
    observation_pattern = r"Observation:\s*(.+?)(?=Thought:|$)"
    final_answer_pattern = r"Final Answer:\s*(.+?)$"

    # 플래그를 사용하여 여러 줄 매칭
    flags = re.DOTALL | re.IGNORECASE

    # 각 부분 추출
    thought_match = re.search(thought_pattern, output, flags)
    action_match = re.search(action_pattern, output, flags)
    action_input_match = re.search(action_input_pattern, output, flags)
    observation_match = re.search(observation_pattern, output, flags)
    final_answer_match = re.search(final_answer_pattern, output, flags)

    # Thought는 필수
    if not thought_match:
        raise ValueError(f"No Thought found in output: {output}")

    thought = thought_match.group(1).strip()

    # Final Answer가 있으면 최종 단계
    if final_answer_match:
        return ReactStep(thought=thought, final_answer=final_answer_match.group(1).strip())

    # Action과 Action Input 파싱
    action = action_match.group(1).strip() if action_match else None
    action_input = None

    if action_input_match:
        action_input_str = action_input_match.group(1).strip()
        try:
            # JSON 파싱 시도
            action_input = json.loads(action_input_str)
        except json.JSONDecodeError:
            # JSON이 아니면 문자열로 처리
            action_input = {"input": action_input_str}

    observation = observation_match.group(1).strip() if observation_match else None

    return ReactStep(thought=thought, action=action, action_input=action_input, observation=observation)


class ReactAgent(BaseAgent):
    """동기 React Agent"""

    def __init__(self, llm: BaseLLM, tools: List[Tool], **kwargs):
        super().__init__(llm, tools, **kwargs)

        # 템플릿이 제공되지 않으면 기본 템플릿 사용
        if "system_prompt_template" in kwargs:
            self.system_prompt_template = kwargs["system_prompt_template"]
        else:
            if DJANGO_AVAILABLE and get_template:
                try:
                    self.system_prompt_template = get_template("prompts/react/system.md")
                except Exception:
                    # Django 설정이 없는 경우 기본 템플릿 사용
                    self.system_prompt_template = SimpleTemplate(self._get_default_system_prompt())
            else:
                # Django가 없는 경우 기본 템플릿 사용
                self.system_prompt_template = SimpleTemplate(self._get_default_system_prompt())

        if "user_prompt_template" in kwargs:
            self.user_prompt_template = kwargs["user_prompt_template"]
        else:
            if DJANGO_AVAILABLE and get_template:
                try:
                    self.user_prompt_template = get_template("prompts/react/user.md")
                except Exception:
                    # Django 설정이 없는 경우 기본 템플릿 사용
                    self.user_prompt_template = SimpleTemplate(self._get_default_user_prompt())
            else:
                # Django가 없는 경우 기본 템플릿 사용
                self.user_prompt_template = SimpleTemplate(self._get_default_user_prompt())

        self.verbose = kwargs.get("verbose", False)

    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트 반환"""
        return """You are an AI assistant that follows the ReAct (Reasoning and Acting) framework to solve problems step by step.

You have access to the following tools:
{% for tool in tools %}
- **{{ tool.name }}**: {{ tool.description }}
{% endfor %}

To solve the user's request, you should follow this exact format:

Question: [The user's question will be here]

Thought: [Your reasoning about what to do next]
Action: [The name of the tool to use, must be one of: {{ tool_names }}]
Action Input: [The input to the tool as JSON format]
Observation: [The result from the tool will appear here]

You can repeat the Thought/Action/Action Input/Observation cycle as many times as needed.

When you have the final answer, use this format:
Thought: I now have enough information to answer the question
Final Answer: [Your complete answer to the user's question]

Important guidelines:
1. Always start with a Thought
2. Action must be exactly one of the available tool names
3. Action Input must be valid JSON that matches the tool's expected parameters
4. Wait for the Observation before proceeding to the next thought
5. Be concise but thorough in your reasoning
6. If a tool returns an error, think about how to fix it or try a different approach"""

    def _get_default_user_prompt(self) -> str:
        """기본 사용자 프롬프트 반환"""
        return "Question: {{ question }}{% if history %}\n\n{{ history }}{% endif %}"

    def _format_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        context = {"tools": self.tools, "tool_names": ", ".join(tool.name for tool in self.tools)}

        # Django 템플릿인지 확인
        if (
            DJANGO_AVAILABLE
            and hasattr(self.system_prompt_template, "render")
            and hasattr(self.system_prompt_template, "origin")
        ):
            return self.system_prompt_template.render(Context(context))
        else:
            # SimpleTemplate
            return self.system_prompt_template.render(context)

    def _format_user_prompt(self, question: str, history: str = "") -> str:
        """사용자 프롬프트 생성"""
        context = {"question": question, "history": history}

        # Django 템플릿인지 확인
        if (
            DJANGO_AVAILABLE
            and hasattr(self.user_prompt_template, "render")
            and hasattr(self.user_prompt_template, "origin")
        ):
            return self.user_prompt_template.render(Context(context))
        else:
            # SimpleTemplate
            return self.user_prompt_template.render(context)

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """도구 실행"""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(t.name for t in self.tools)}"

        # 검증 수행
        is_valid, error_msg = tool.validate_input(**tool_input)
        if not is_valid:
            return f"Validation error: {error_msg}"

        try:
            # 도구 실행
            result = ToolExecutor.execute_tool(tool, **tool_input)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Execution error: {str(e)}"

    def run(self, input: str) -> str:
        """Agent 실행"""
        # 시스템 프롬프트 설정
        original_system_prompt = self.llm.system_prompt
        self.llm.system_prompt = self._format_system_prompt()

        try:
            history = ""

            for iteration in range(self.max_iterations):
                # 프롬프트 생성
                prompt = self._format_user_prompt(input, history)

                # LLM 호출
                response = self.llm.ask(prompt)
                # Reply 객체를 문자열로 변환
                response = str(response)

                if self.verbose:
                    logger.info(f"Iteration {iteration + 1}:\n{response}")

                # 응답 파싱
                try:
                    step = parse_react_output(response)
                except ValueError as e:
                    logger.error(f"Parsing error: {e}")
                    history += f"\n{response}\nError: Failed to parse response. Please follow the correct format.\n"
                    continue

                # 최종 답변인 경우
                if step.is_final:
                    return step.final_answer

                # 액션 실행
                if step.action and step.action_input:
                    observation = self._execute_tool(step.action, step.action_input)
                    history += f"\n{response}\nObservation: {observation}\n"
                else:
                    history += f"\n{response}\nError: Action and Action Input are required.\n"

            # 최대 반복 횟수 도달
            return f"Reached maximum iterations ({self.max_iterations}) without finding a final answer."

        finally:
            # 원래 시스템 프롬프트 복원
            self.llm.system_prompt = original_system_prompt


class AsyncReactAgent(AsyncBaseAgent):
    """비동기 React Agent"""

    def __init__(self, llm: BaseLLM, tools: List[Tool], **kwargs):
        super().__init__(llm, tools, **kwargs)

        # 템플릿이 제공되지 않으면 기본 템플릿 사용
        if "system_prompt_template" in kwargs:
            self.system_prompt_template = kwargs["system_prompt_template"]
        else:
            if DJANGO_AVAILABLE and get_template:
                try:
                    self.system_prompt_template = get_template("prompts/react/system.md")
                except Exception:
                    # Django 설정이 없는 경우 기본 템플릿 사용
                    self.system_prompt_template = SimpleTemplate(self._get_default_system_prompt())
            else:
                # Django가 없는 경우 기본 템플릿 사용
                self.system_prompt_template = SimpleTemplate(self._get_default_system_prompt())

        if "user_prompt_template" in kwargs:
            self.user_prompt_template = kwargs["user_prompt_template"]
        else:
            if DJANGO_AVAILABLE and get_template:
                try:
                    self.user_prompt_template = get_template("prompts/react/user.md")
                except Exception:
                    # Django 설정이 없는 경우 기본 템플릿 사용
                    self.user_prompt_template = SimpleTemplate(self._get_default_user_prompt())
            else:
                # Django가 없는 경우 기본 템플릿 사용
                self.user_prompt_template = SimpleTemplate(self._get_default_user_prompt())

        self.verbose = kwargs.get("verbose", False)

    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트 반환"""
        return """You are an AI assistant that follows the ReAct (Reasoning and Acting) framework to solve problems step by step.

You have access to the following tools:
{% for tool in tools %}
- **{{ tool.name }}**: {{ tool.description }}
{% endfor %}

To solve the user's request, you should follow this exact format:

Question: [The user's question will be here]

Thought: [Your reasoning about what to do next]
Action: [The name of the tool to use, must be one of: {{ tool_names }}]
Action Input: [The input to the tool as JSON format]
Observation: [The result from the tool will appear here]

You can repeat the Thought/Action/Action Input/Observation cycle as many times as needed.

When you have the final answer, use this format:
Thought: I now have enough information to answer the question
Final Answer: [Your complete answer to the user's question]

Important guidelines:
1. Always start with a Thought
2. Action must be exactly one of the available tool names
3. Action Input must be valid JSON that matches the tool's expected parameters
4. Wait for the Observation before proceeding to the next thought
5. Be concise but thorough in your reasoning
6. If a tool returns an error, think about how to fix it or try a different approach"""

    def _get_default_user_prompt(self) -> str:
        """기본 사용자 프롬프트 반환"""
        return "Question: {{ question }}{% if history %}\n\n{{ history }}{% endif %}"

    def _format_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        context = {"tools": self.tools, "tool_names": ", ".join(tool.name for tool in self.tools)}

        # Django 템플릿인지 확인
        if (
            DJANGO_AVAILABLE
            and hasattr(self.system_prompt_template, "render")
            and hasattr(self.system_prompt_template, "origin")
        ):
            return self.system_prompt_template.render(Context(context))
        else:
            # SimpleTemplate
            return self.system_prompt_template.render(context)

    def _format_user_prompt(self, question: str, history: str = "") -> str:
        """사용자 프롬프트 생성"""
        context = {"question": question, "history": history}

        # Django 템플릿인지 확인
        if (
            DJANGO_AVAILABLE
            and hasattr(self.user_prompt_template, "render")
            and hasattr(self.user_prompt_template, "origin")
        ):
            return self.user_prompt_template.render(Context(context))
        else:
            # SimpleTemplate
            return self.user_prompt_template.render(context)

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """비동기 도구 실행"""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(t.name for t in self.tools)}"

        # 검증 수행
        is_valid, error_msg = tool.validate_input(**tool_input)
        if not is_valid:
            return f"Validation error: {error_msg}"

        try:
            # 도구 실행
            result = await ToolExecutor.aexecute_tool(tool, **tool_input)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Execution error: {str(e)}"

    async def arun(self, input: str) -> str:
        """비동기 Agent 실행"""
        # 시스템 프롬프트 설정
        original_system_prompt = self.llm.system_prompt
        self.llm.system_prompt = self._format_system_prompt()

        try:
            history = ""

            for iteration in range(self.max_iterations):
                # 프롬프트 생성
                prompt = self._format_user_prompt(input, history)

                # LLM 호출
                if hasattr(self.llm, "aask"):
                    response = await self.llm.aask(prompt)
                else:
                    # 동기 LLM을 비동기로 실행
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, self.llm.ask, prompt)

                # Reply 객체를 문자열로 변환
                response = str(response)

                if self.verbose:
                    logger.info(f"Iteration {iteration + 1}:\n{response}")

                # 응답 파싱
                try:
                    step = parse_react_output(response)
                except ValueError as e:
                    logger.error(f"Parsing error: {e}")
                    history += f"\n{response}\nError: Failed to parse response. Please follow the correct format.\n"
                    continue

                # 최종 답변인 경우
                if step.is_final:
                    return step.final_answer

                # 액션 실행
                if step.action and step.action_input:
                    observation = await self._execute_tool(step.action, step.action_input)
                    history += f"\n{response}\nObservation: {observation}\n"
                else:
                    history += f"\n{response}\nError: Action and Action Input are required.\n"

            # 최대 반복 횟수 도달
            return f"Reached maximum iterations ({self.max_iterations}) without finding a final answer."

        finally:
            # 원래 시스템 프롬프트 복원
            self.llm.system_prompt = original_system_prompt


def create_react_agent(llm: BaseLLM, tools: List[Tool], **kwargs) -> Union[ReactAgent, AsyncReactAgent]:
    """
    React Agent를 생성하는 팩토리 함수

    Args:
        llm: 사용할 LLM
        tools: 사용할 도구들
        **kwargs: 추가 옵션

    Returns:
        ReactAgent 또는 AsyncReactAgent 인스턴스
    """
    # 비동기 도구가 있는지 확인
    has_async_tools = any(tool.is_async for tool in tools)

    # 비동기 도구가 있으면 AsyncReactAgent 생성
    if has_async_tools:
        return AsyncReactAgent(llm, tools, **kwargs)
    else:
        return ReactAgent(llm, tools, **kwargs)


__all__ = [
    "ReactAgent",
    "AsyncReactAgent",
    "create_react_agent",
    "parse_react_output",
    "ReactStep",
]
