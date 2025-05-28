# LLM ask 메서드의 choices 파라미터 사용 가이드

## 개요

`ask` 메서드에 `choices` 파라미터가 추가되어, LLM에게 특정 선택지 중에서 하나를 선택하도록 강제할 수 있습니다. 이제 별도의 `select` 메서드 없이 `ask` 메서드로 모든 기능을 통합하여 사용할 수 있습니다.

## 기본 사용법

```python
from pyhub.llm import LLM

# LLM 인스턴스 생성
llm = LLM.create("gpt-4o-mini")

# choices를 사용한 ask
reply = llm.ask(
    input="어떤 프로그래밍 언어가 웹 백엔드에 가장 적합한가요?",
    choices=["Python", "JavaScript", "Go", "Ruby"]
)

# Reply 객체에서 선택된 값 확인
print(reply.choice)  # "Python" 또는 다른 선택지
print(reply.choice_index)  # 선택된 인덱스 (0부터 시작)
print(reply.confidence)  # 선택의 신뢰도 (0.0 ~ 1.0)
```

## Reply 객체의 변화

choices를 사용하면 Reply 객체에 추가 정보가 포함됩니다:

```python
@dataclass
class Reply:
    text: str = ""  # 원본 응답 텍스트
    usage: Optional[Usage] = None
    # choices 사용 시 설정되는 필드들
    choice: Optional[str] = None  # 선택된 값
    choice_index: Optional[int] = None  # 선택된 인덱스
    confidence: Optional[float] = None  # 선택 신뢰도
```

## 고급 사용법

### 1. 컨텍스트와 함께 사용

```python
# 문자열 컨텍스트
reply = llm.ask(
    input="다음 중 가장 적합한 데이터베이스를 선택하세요",
    choices=["PostgreSQL", "MongoDB", "Redis", "MySQL"],
    context={"requirements": "ACID 준수, 복잡한 쿼리 지원"}
)

# 복잡한 컨텍스트
context = {
    "project_type": "금융 거래 시스템",
    "requirements": ["트랜잭션 지원", "강력한 일관성", "복잡한 JOIN"],
    "scale": "중대형"
}

reply = llm.ask(
    input=context,
    choices=["PostgreSQL", "MongoDB", "Cassandra"],
)
print(f"선택: {reply.choice}")  # 아마도 "PostgreSQL"
```

### 2. choices_optional 옵션 (적절한 선택지가 없는 경우)

```python
# 적절한 선택지가 없으면 None 반환 가능
reply = llm.ask(
    input="PHP 웹 프레임워크를 선택하세요",
    choices=["Django", "FastAPI", "Flask"],
    choices_optional=True
)

if reply.choice is None:
    print("제시된 선택지 중 적절한 것이 없습니다")
else:
    print(f"선택: {reply.choice}")
```

### 3. 스트리밍 모드에서도 지원

```python
# 스트리밍 모드
for chunk in llm.ask(
    input="가장 인기 있는 프론트엔드 프레임워크는?",
    choices=["React", "Vue", "Angular"],
    stream=True
):
    if chunk.text:
        print(chunk.text, end="")  # 응답 텍스트 스트리밍
    if chunk.choice is not None:
        print(f"\n최종 선택: {chunk.choice}")  # 마지막에 선택 정보
```

### 4. 비동기 모드

```python
# 비동기 사용
reply = await llm.ask_async(
    input="최적의 클라우드 서비스는?",
    choices=["AWS", "Google Cloud", "Azure"],
    context="스타트업, 비용 민감"
)
print(reply.choice)
```

## Provider별 구현 특징

### OpenAI (가장 정확)
- **JSON Schema**를 통한 structured output 사용
- `response_format`으로 선택지를 강제
- 100% 정확한 선택 보장
- confidence 정보 제공

### Anthropic
- 강력한 시스템 프롬프트로 선택 강제
- 텍스트 매칭으로 선택 확인
- 대소문자 무시 및 부분 매칭 지원

### Google, Upstage, Ollama
- 프롬프트 기반 처리
- 낮은 temperature로 일관성 확보

## 실제 사용 예시

### 기술 스택 선택
```python
# 프로젝트에 맞는 기술 선택
tech_stack = {}

# 언어 선택
reply = llm.ask(
    input={
        "task": "웹 API 서버 개발",
        "requirements": ["비동기 지원", "타입 안전성", "빠른 성능"]
    },
    choices=["Python", "TypeScript", "Go", "Rust"]
)
tech_stack["language"] = reply.choice

# 프레임워크 선택
reply = llm.ask(
    input=f"{tech_stack['language']}로 REST API를 만들 때 최적의 프레임워크는?",
    choices=["FastAPI", "Django", "Flask"] if tech_stack["language"] == "Python" else ["Express", "Nest.js", "Fastify"]
)
tech_stack["framework"] = reply.choice

print(f"추천 스택: {tech_stack}")
```

### 의사결정 자동화
```python
def choose_deployment_strategy(app_info):
    """배포 전략 자동 선택"""
    reply = llm.ask(
        input=app_info,
        choices=["Container (Docker)", "Serverless", "Traditional VM", "Static Hosting"],
        choices_optional=True
    )
    
    if reply.choice is None:
        return "Manual review required"
    
    if reply.confidence < 0.7:
        return f"Low confidence ({reply.confidence:.2f}): {reply.choice} (needs review)"
    
    return reply.choice

# 사용
app_info = {
    "type": "Static website",
    "features": ["No backend", "CDN required", "Simple HTML/CSS/JS"],
    "traffic": "Medium"
}

strategy = choose_deployment_strategy(app_info)
print(f"배포 전략: {strategy}")
```

### A/B 테스트 변형 선택
```python
# 여러 선택을 연속으로
variations = {}

# 색상 선택
reply = llm.ask(
    input="전자상거래 사이트의 구매 버튼 색상",
    choices=["Green", "Blue", "Orange", "Red"],
    context="높은 전환율, 신뢰감"
)
variations["button_color"] = reply.choice

# 텍스트 선택
reply = llm.ask(
    input="구매 버튼 텍스트",
    choices=["Buy Now", "Add to Cart", "Purchase", "Get It Now"],
    context=f"Color: {variations['button_color']}, Target: Young adults"
)
variations["button_text"] = reply.choice

print(f"A/B 테스트 변형: {variations}")
```

## 마이그레이션 가이드

기존 `select` 메서드 사용 코드를 `ask`로 변경:

```python
# 기존 코드 (제거됨)
result = llm.select(
    choices=["A", "B", "C"],
    context="Choose the best option"
)

# 새로운 코드
reply = llm.ask(
    input="Choose the best option",
    choices=["A", "B", "C"]
)
result = reply.choice
```

## 주의사항

1. **최소 2개의 선택지**: choices는 반드시 2개 이상이어야 합니다
2. **Reply 객체 사용**: 반환값은 문자열이 아닌 Reply 객체입니다
3. **choice 필드 확인**: 선택된 값은 `reply.choice`에서 확인
4. **None 처리**: `choices_optional=True`일 때 `reply.choice`가 None일 수 있음

## 성능 고려사항

- OpenAI의 structured output은 첫 호출 시 약간의 지연 발생
- 모든 choices 호출은 자동으로 캐싱됨
- 스트리밍 모드에서는 마지막 chunk에 choice 정보 포함