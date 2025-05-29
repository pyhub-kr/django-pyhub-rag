"""React Agent 사용 예제"""

import asyncio
from pyhub.llm import LLM
from pyhub.llm.agents import Tool, create_react_agent
from pyhub.llm.agents.tools import Calculator


def sync_example():
    """동기 React Agent 예제"""
    print("=== 동기 React Agent 예제 ===\n")
    
    # LLM 생성
    llm = LLM.create(model="gpt-4o-mini")
    
    # 도구 생성
    tools = [
        Tool(
            name="calculator",
            description="Performs mathematical calculations. Use this when you need to compute numbers.",
            func=Calculator().run,
            args_schema=Calculator().args_schema
        )
    ]
    
    # Agent 생성
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        verbose=True  # 상세 로그 출력
    )
    
    # 질문 실행
    questions = [
        "What is 25 * 4?",
        "Calculate the square root of 144",
        "What is (10 + 5) * 3 - 20?",
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        result = agent.run(question)
        print(f"Answer: {result}\n")
        print("-" * 50)


async def async_example():
    """비동기 React Agent 예제"""
    print("\n=== 비동기 React Agent 예제 ===\n")
    
    # 비동기 도구 생성
    async def async_calculator(expression: str) -> str:
        """비동기 계산기"""
        calc = Calculator()
        # 실제로는 동기 함수지만 예제를 위해 비동기로 래핑
        return calc.run(expression=expression)
    
    # LLM 생성
    llm = LLM.create(model="gpt-4o-mini")
    
    # 도구 생성
    tools = [
        Tool(
            name="calculator",
            description="Performs mathematical calculations asynchronously.",
            func=async_calculator,
            args_schema=Calculator().args_schema
        )
    ]
    
    # AsyncReactAgent가 자동으로 생성됨
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        verbose=False
    )
    
    # 질문 실행
    question = "Calculate 100 divided by 4, then multiply the result by 2"
    print(f"Question: {question}")
    result = await agent.arun(question)
    print(f"Answer: {result}")


def main():
    """메인 함수"""
    # 동기 예제 실행
    sync_example()
    
    # 비동기 예제 실행
    asyncio.run(async_example())


if __name__ == "__main__":
    main()