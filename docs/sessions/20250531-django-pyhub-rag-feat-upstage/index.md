# 장고 기반으로 PDF 파싱부터 문서 기반 RAG 까지 (2025년 5월 31일)

<div class="video-container">
<iframe src="https://www.youtube.com/embed/1aQH5x49Nic?si=dtgtDRfXAefOO7V2" allowfullscreen></iframe>
</div>

+ [PDF 슬라이드 다운로드](./slide.pdf)

!!! TODO

    내용을 아래에 정리 중.

---

## 다룰 내용

+ django-pyhub-rag 라이브러리와 업스테이지 Document Parse API 통합
    - PDF 파싱 + 이미지 추출, 이미지 설명 작성까지 1번의 명령으로 수행
+ 장고 모델 기반의 강력한 문서 기반 RAG 시스템을 구현하는 전체 과정(장고 프로젝트 생성부터)을 라이브 시연

## RAG

> 검색 증강 생성 (Retrieval Augmented Generation)

## 문서 변환

> 문서 레이아웃을 살려 Plain Text로 변환

### 업스테이지 API 요청 예시

> 업스테이지 Document Parse API 활용 ($0.01 / 페이지)

+ 샘플 코드 : [https://console.upstage.ai/docs/capabilities/document-digitization/document-parsing#example](https://console.upstage.ai/docs/capabilities/document-digitization/document-parsing#example)
+ 샘플 파일 : [https://github.com/pyhub-kr/django-pyhub-rag/tree/main/samples](https://github.com/pyhub-kr/django-pyhub-rag/tree/main/samples)

``` python
import json
import requests
import os

# API Key 지정 : https://console.upstage.ai/api-keys?api=document-parsing
API_KEY = os.getenv("UPSTAGE_API_KEY")

filepath = "./samples/현대 싼타페 2025 Hyundai Owner's Manual.pdf"  # 입력 파일 : 743 페이지 ($7.43)

url = "https://api.upstage.ai/v1/document-digitization"
headers = {"Authorization": f"Bearer {API_KEY}"}

files = {"document": open(filepath, "rb")}
data = {
    "ocr": "force",
    "model": "document-parse",
    "align_orientation": True,              # 문서 방향 자동 조정
    "coordinates": True,                    # 위치 인식
    "output_formats": "['markdown']",       # or 'html', 'text'
    # 지정 레이아웃 타입의 컨텐츠를 base64 이미지로서 받기
    # https://console.upstage.ai/docs/capabilities/document-digitization/document-parsing#understanding-the-outputs
    "base64_encoding": "['chart', 'equation', 'figure', 'table']",
}
response = requests.post(url, headers=headers, files=files, data=data)

# API 응답을 파일에 쓰기
with open("./samples/현대 싼타페 2025 Hyundai Owner's Manual.json", "wt", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=4, ensure_ascii=False)
```

### django-pyhub-rag 활용

``` shell
pip install --upgrade "django-pyhub-rag[all]"

# 변환 명령 : UPSTAGE_API_KEY, OPENAI_API_KEY 환경변수 필요
python -m pyhub.parser upstage --enable-image-descriptor 파일경로.pdf
python -m pyhub.parser upstage -i 파일경로.pdf
# API 캐시 활성화 : 파일 시스템 캐시, 최대 5000개, 타임아웃 3일
python -m pyhub.parser upstage --enable-cache -i 파일경로.pdf
```

### 이미지 설명 스크립트, 커스텀 지원

``` shell title="pyhub mcptools 설정파일 생성, 경로, 출력, 수정"
python -m pyhub toml create # 설정파일 생성
python -m pyhub toml path   # 설정파일 경로 출력
python -m pyhub toml show   # 설정파일 내용 표준출력
python -m pyhub toml edit   # 설정파일 편집
```

### 랭체인, UpstageDocumentParseParser

동기 방식만 지원

+ [GitHub 저장소](https://github.com/langchain-ai/langchain-upstage/blob/main/libs/upstage/langchain_upstage/document_parse_parsers.py#L169)
+ 배치크기 옵션
    - API 호출 시, 여러 페이지 지원 여부
    - 배치 여부 지정 (1페이지 or 10페이지)
+ 문서 머지 전략
    - page, element, none

### django-pyhub-rag, UpstageDocumentParseParser

동기/비동기 방식 지원

+ 배치크기 옵션
    - API 호출 시, 여러 페이지 지원 여부
    - 배치 크기 직접 지정 지원
+ 문서 머지 전략
    - page, element, none
+ 다양한 페이지 번호 지정 지원
+ LLM통한 이미지 설명 지원
+ API 캐싱 지원 (장고 캐싱 기반)
    - 동일 페이지에 대해서는 API 요청 X (배치 크기=1 지정 필요)
+ 비동기 지원
+ 장고 File API 기반으로 다양한 스토리지 지원
    - AWS S3, Azure Storage 등 상의 PDF 읽기 가능

``` python title="src/pyhub/parser/upstage/parser.py"

from django.core.files import File

class UpstageDocumentParseParser:
    # ...

    async def _call_document_parse_api(self, files: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
        headers = {
            "Authorization": f"Bearer {self.upstage_api_key}",
        }
        data = {
            "ocr": self.ocr_mode,
            "model": self.model,
            "output_formats": "['html', 'text', 'markdown']",
            "coordinates": self.coordinates,
            "base64_encoding": "[" + ",".join(f"'{el}'" for el in self.base64_encoding_category_list) + "]",
        }

        response_data: bytes = await cached_http_async(
            self.api_url,
            method="POST",
            headers=headers,
            data=data,
            files=files,
            timeout=timeout,
            ignore_cache=self.ignore_cache,
            cache_alias="upstage",
        )
        return json.loads(response_data)
```

## pyhub.llm 활용 예시

### LLM 응답 생성

> OpenAI, Anthropic, Google, Upstage, Ollama을 단일 인터페이스로 지원

``` python
from pyhub.llm import OpenAILLM
# UpstageLLM, AnthropicLLM, GoogleLLM, OllamaLLM

llm = OpenAILLM(
    # model="gpt-4o-mini",
    # temperature=0.2,
    # max_tokens=1000,
    # api_key=  # default: OPENAI_API_KEY 환경변수
)

reply = llm.ask("hello")
print(reply)
print(reply.usage)
```

### LLM.create

> 지원 모델명 타입으로 자동 완성 지원

``` python
from pyhub.llm import LLM

# 여러 LLM API를 활용해야할 때, model명 지정 만으로 손쉽게 스위칭
llm = LLM.create(model="gemini-1.5-flash")
# llm = GoogleLLM(model="gemini-1.5-flash") 과 동일

reply = llm.ask("hello")
print(reply)
print(reply.usage)
```

### stream 지원

> Generator[Reply] 반환. 마지막 chunk 응답에 usage

``` python
for reply in llm.ask("대전 여행지 3곳 알려줘", stream=True)
    print(reply.text, end="", flush=True)
print()
print(reply.usage)
```

### 선택 지원

> OpenAI/Upstage API에서는 Structured Output 활용하여, 보다 견고한 선택 지원

``` python
from pyhub.llm import OpenAILLM

llm = OpenAILLM()

reply = llm.ask("과일을 골라줘.", choices=["apple", "car"])
print(repr(reply))
print(reply.choice)        # Optional[str] : 선택할 수 없다면 None
print(reply.choice_index)  # Optional[int] : 선택할 수 없다면 None
print(reply.usage)
```

출력

```
Reply(text='{"choice": "apple", "confidence": 0.85}', choice='apple', choice_index=0, confidence=0.85)
apple
0
Usage(input=65, output=11)
```

### 프롬프트 템플릿 지원

> 캐싱, 템플릿, 모델 등의 장고 기능을 활용할 때에는 pyhub.init() 호출 필요

``` python
from pyhub.llm import OpenAILLM

llm = OpenAILLM(system_prompt="너는 유능한 여행 가이드",
                prompt="{여행지}의 맛집을 10개 소개해줘")
reply = llm.ask({"여행지": "대전"})
print(reply.text[:100], "...")
print(reply.usage)
```

``` python
from pyhub import init
from pyhub.llm import OpenAILLM

init()

# 프롬프트 템플릿 지원
llm = OpenAILLM(
    system_prompt="너는 유능한 여행 가이드",
    prompt="""
다음은 맛집 {{ 맛집 }}의 대표 메뉴.

{% for 메뉴 in 메뉴_리스트 %}
- {{ 메뉴.이름 }}
{% endfor %}

맛집 소개 블로그 글을 써줘.
    """,
)

reply_generator = llm.ask({
    "맛집": "성심당",
    "메뉴_리스트": [
        {"이름": "튀김소보로" },
        {"이름": "튀소구마" },
        {"이름": "판타롱 부추빵" },
        {"이름": "시루 시리즈" },
        {"이름": "명란바게트" },
        {"이름": "보문산메아리" },
    ],
}, stream=True)

for reply in reply_generator:
    print(reply.text, end="", flush=True)
print()
print(reply.usage)
```

### 파일 업로드 지원

> Vision Language Model API 지정 필요
 
``` python
from pyhub.llm import OpenAILLM

llm = OpenAILLM()  # 디폴트 : gpt-4o-mini

from pathlib import Path
from typing import Union
from django.core.files import File

# pyhub.llm describe 명령과 동일
files: list[Union[str, Path, File]] = [
    # "./sample1.jpg",  # 파일경로/URL 문자열 및 Path 객체, 장고 File 객체 지원
    "https://raw.githubusercontent.com/pyhub-kr/dump-data/refs/heads/main/sample1.jpg",
]
reply = llm.ask("Explain this image in korean", files=files)
print(reply)
```

### 임베딩 지원

> Anthropic를 제외한 OpenAI, Google, Upstage, Ollama 지원.

``` python
# 임베딩 지원 (단일 문자열)
#  - OpenAILLM 디폴트 임베딩 모델 : text-embeddding-3-small
embeded = llm.embed("문서 내용 1")
print(len(embeded.array), "차원")
print(embeded.array[:3], "...")
print(embeded.usage)
```

``` python
# 임베딩 지원 (단일 문자열)
embeded = llm.embed(["문서 내용 2", "문서 내용 3"])
print(len(embeded.arrays), "개")
print(embeded.arrays[0][:3], "...")
print(embeded.arrays[1][:3], "...")
print(embeded.usage)
```

## 임베딩 및 벡터 스토어에 저장

### Postgres 데이터베이스 + pgvector 확장

supabase 서비스에서도 pgvector 확장 지원 (무료 사용 가능)

+ [pgvector 설치 가이드](https://ai.pyhub.kr/setup/vector-stores/pgvector/)

``` shell title="도커를 활용한 pgvector 데이터베이스 생성"
docker run \
    -e POSTGRES_USER=djangouser \
    -e POSTGRES_PASSWORD=djangopw \
    -e POSTGRES_DB=djangodb \
    -p 5432:5432 \
    -d \
    pgvector/pgvector:pg17
```

``` title=".env 포맷"
DATABASE_URL=postgresql://djangouser:djangopw@localhost:5432/djangodb
```

``` title="requirements.txt"
# 필수
django
pgvector
psycopg2-binary
django-pyhub-rag[all]

# 옵션
django-environ
django-extensions
```

### 장고 프로젝트 샘플 settings

먼저 장고 프로젝트를 생성하신 후에 아래 settings 적용

``` python title="mysite/settings.py"
# mysite/settings.py

from pathlib import Path
from environ import Env

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()

env_path = BASE_DIR / ".env"
if env_path.is_file():
    env.read_env(env_path, overwrite=True)

# ...

INSTALLED_APPS = [
    # ...
    "pyhub.rag",  # django-pyhub-rag 앱
    "django_extensions",
]
```

이어서 `myrag` 장고 앱을 생성하신 후에, `INSTALLED_APPS` 리스트에 `myrag` 추가

``` python title="mysite/settings.py"
INSTALLED_APPS = [
    # ...
    "myrag",      # myrag 앱 생성 후에 추가
]
```

`DATABASE_URL` 환경변수 값을 파싱하여, 데이터베이스 설정에 반영되도록 `env.db()` 적용

``` python title="mysite/settings.py"
DATABASES = {
    "default": env.db(),  # DATABASE_URL 환경변수 파싱
}
```

### pgvector 파이썬 라이브러리에서 django 모델 지원

> `VectorField`만 추가하면 기존 프로젝트/서비스에서 OK. => 운영 단순화

### django-pyhub-rag 활용

관계형 데이터와 베겉 데이터를 단일 쿼리로 처리.

- 카테고리 필터링과 벡터 유사도 검색을 단일 쿼리셋으로 처리
- 자연스러운 JOIN 연산 (`select_related`, `prefetch_related` ok)


> 벡터 모델 지원 + 임베딩 지원 + LLM 지원

``` python title="myrag/models.py"
from django.db import models
from pyhub.rag.models.postgres import PGVectorDocument

# 디폴트로 page_content, metadata, embedding 필드 정의
#  - embeding 필드 재정의 : 임베딩 차원 수, 임베딩 모델 변경이 필요할 때
class VectorDocument(PGVectorDocument):
    # category = models.ForeignKey("Category",
    #     on_delete=models.CASCADE)

    class Meta:
        indexes = [
            PGVectorDocument.make_hnsw_index(
                "myrag_vd_emb_idx"
            ),
        ]
```

이후 생성되는 마이그레이션 파일의 operations 리스트 처음에 `VectorExtension()` 추가

``` python title="myrag/migrations/0001_initial.py"

from pgvector.django import VectorExtension

class Migration(migrations.Migration):
    operations = [
        VectorExtension()  # vector 확장 활성화
        # ...
    ]
```

``` python title="유사 문서 검색 (by 코사인 유사도) - 디폴트 모델 매니저를 통한 지원"
qs = VectorDocument.objects.all()  # 필요한 만큼 조건을 추가한 뒤에
docs = qs.similarity_search("유사문서 찾을 내용")
# docs = await qs.similarity_search_async("유사문서 찾을 내용")
```

### 임베딩 + 벡터 스토어에 저장

> page_content 필드가 변경되면, 자동으로 embedding 필드 업데이트 수행

방법 1) pyhub.rag 장고 관리 명령을 통한 임베딩 + 벡터 스토어 저장

```
❯ python manage.py load_jsonl myrag.VectorDocument ./hyundai.jsonl
Created final batch of 84 instances
Successfully created 84 instances in total
```

방법 2) 쿼리셋을 통한 직접 임베딩 + 벡터 스토어 저장

``` python
import json
from myrag.models import VectorDocument

jsonl_path = "./hyundai.jsonl"

vector_document_list = []

for line in open(jsonl_path, "rt", encoding="utf-8"):
    line = line.strip()
    if line:
        obj = json.loads(line)
        # embedding 필드 값이 없는 인스턴스에 대해서는
        # 모아서 bulk embedding API 요청
        vector_document = VectorDocument(
            page_content=obj["page_content"],
            metadata=obj["metadata"],
        )
        vector_document_list.append(vector_document)

VectorDocument.objects.bulk_create(
    vector_document_list,
    batch_size=1000,
)
```

저장된 레코드 개수 확인 및 임베딩 필드 확인

``` python
print(VectorDocument.objects.first().embedding)
print(VectorDocument.objects.all().count())
```

## 유사 문서 검색 및 RAG 채팅

### 유사 문서 검색

embedding 필드에 지정된 LLM 모델을 활용하여 자동으로 쿼리 임베딩 생성한 후에, 유사 문서 검색

``` python title="[django-extensions] shell_plus --print-sql 명령으로 쉘 구동"
>>> docs = VectorDocument.objects.similarity_search("등받이 각도")
>>> for doc in docs:
...     print(doc.distance, doc.page_content[:100] + '...')
...

SELECT "myrag_vectordocument"."id",
       "myrag_vectordocument"."page_content",
       "myrag_vectordocument"."metadata",
       ("myrag_vectordocument"."embedding" <=> '[0.02761758863925934,
           -0.014913497492671013,
           0.03034409135580063,

Execution time: 0.004041s [Database: default]
```

출력

```
0.5975217401242773 3

# 등받이 각도 조절(2)(전동식)

등받이 각도 조절 스위치(2) 윗부분을 앞으로 당기면 등받이가 앞으로 숙여지고, 뒤로 당기면 등
받이가 뒤로 젖혀집니다.

# 등받이 접...
0.6264605820178986 3

- 2: 등받이 각도 조절
- 3: 좌석 높낮이 조절(사양 적용 시)
- 4: 쿠션 각도 조절(사양 적용 시)
- 5: 다리 받침대 조절 스위치(사양 적용 시)
- 6: 릴렉...
0.6310898817884755 # 시트 및 안전 장치

등받이 각도 조절 스위치 윗부분을 앞으로 당기면 등받이가 앞으로 숙여지고, 뒤로 밀면 등받이가
뒤로 젖혀집니다.

# 쿠션 각도/높낮이 조절하기

![im...
0.6466300767627413 3

전동식

![image](p021/02-figure.jpg)
2
4

- 1 등받이 각도 조절 레버 또는 스위치(1)로 좌석 등받이를 뒤로 젖히십시오(2).
- 2 헤드레스트...
```

### RAG 채팅 비교

=== "django-pyhub-rag 버전"

    ``` python
    # 별도 파이썬 스크립트 구동 시에 장고 프로젝트 초기 로딩
    import os
    from typing import Generator
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    import django; django.setup()
    
    # 장고 프로젝트 초기 로딩 후에 수행
    from pyhub.llm import OpenAILLM, AnthropicLLM, UpstageLLM, GoogleLLM
    from myrag.models import VectorDocument
    
    
    class ChatLLM:
        def __init__(self):
            system_prompt = """현대 산타페 자동차 매뉴얼을 기반으로 정확하게 답변하세요.
                               매뉴얼에 없는 내용은 모른다고 대답하세요. 사실과 의견을 구별해서 대답하세요."""
    #       self.llm = OpenAILLM(system_prompt=system_prompt, model="gpt-4o",
    #                            temperature=0.7, max_tokens=8192)
            self.llm = UpstageLLM(system_prompt=system_prompt, model="solar-pro2-preview",
                                  temperature=0.7, max_tokens=8192)
    
        def ask(self, user_input: str) -> Generator[str, None, None]:
            for reply in self.llm.ask(user_input, stream=True):
                yield reply.text


    class RAGDecisionLLM:
        def __init__(self):
            system_prompt = """
                사용자 질문이 '현대 산타페 자동차 매뉴얼'의 내용을 기반으로 검색(RAG)이 필요한지 판단하세요.
                - 매뉴얼에 나올 법한 질문이면 "RAG"
                - 일반적인 상식이나 매뉴얼과 무관한 질문이면 "NO-RAG
            """
            self.llm = GoogleLLM(system_prompt=system_prompt, model="gemini-2.0-flash-lite")
    
        def should_use_rag(self, question: str) -> bool:
            reply = self.llm.ask(
                input=question,
                # choices 인자가 지정되면 강제로 temperature=0.1로 변경
                # openai llm에서는 Structured Outputs 방식으로 동작
                # https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat
                choices=["RAG", "NO-RAG"],
                use_history=False,
            )
            # return reply.choice == "RAG"
            return reply.choice_index == 0
    ```

=== "랭체인 버전"

    ``` python
    # 별도 파이썬 스크립트 구동 시에 장고 프로젝트 초기 로딩
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    import django; django.setup()
    
    # 장고 프로젝트 초기 로딩 후에 수행
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.chat_history import InMemoryChatMessageHistory
    from langchain_openai import ChatOpenAI
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    from myrag.models import VectorDocument
    
    class ChatLLM:
        def __init__(self):
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7, streaming=True, max_tokens=8192)
            prompt = ChatPromptTemplate.from_messages([
                ("system", """현대 산타페 자동차 매뉴얼을 기반으로 정확하게 답변하세요.
                              매뉴얼에 없는 내용은 모른다고 대답하세요. 사실과 의견을 구별해서 대답하세요."""),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])
            self.history = InMemoryChatMessageHistory()
            self.chain = prompt | llm
    
        def ask(self, user_input: str) -> Generator[str, None, None]:
            stream = self.chain.stream({
                "input": user_input,
                "chat_history": self.history.messages,
            })
    
            full_response = ""
            for chunk in stream:
                yield chunk.content
                full_response += chunk.content
    
            # Add to chat history - store original user input, not the RAG context
            self.history.add_user_message(user_input)
            self.history.add_ai_message(full_response)
    

    class RAGDecisionLLM:
        def __init__(self):
            system_prompt = """
                사용자 질문이 '현대 산타페 자동차 매뉴얼'의 내용을 기반으로 검색(RAG)이 필요한지 판단하세요.
                - 매뉴얼에 나올 법한 질문이면 "RAG"
                - 일반적인 상식이나 매뉴얼과 무관한 질문이면 "NO-RAG
            """
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.1)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Question: {question}")
            ])
            self.chain = prompt | llm | StrOutputParser()
    
        def should_use_rag(self, question: str) -> bool:
            result = self.chain.invoke({"question": question})
            choice = result.strip()
            return choice == "RAG"
    ```

이후 공통 코드

``` python
def main():
    print("🤖 현대 산타페 AI 어시스턴트")

    chat_llm = ChatLLM()
    rag_decision_llm = RAGDecisionLLM()

    while True:
        try:
            user_input = input(">>> ").strip()
            if not user_input: continue

            is_rag = rag_decision_llm.should_use_rag(user_input)

            if is_rag:
                print("INFO: 유사 문서 검색 중 ...")
                docs = VectorDocument.objects.similarity_search(user_input)

                # 출처 정보 추출
                sources = []
                for doc in docs[:5]:  # 상위 5개 문서의 출처만 표시
                    if hasattr(doc, 'metadata') and doc.metadata:
                        source = doc.metadata.get('source', '?')
                        page = doc.metadata.get('page', '?')
                        sources.append(f"{source}/p.{page}")
                    else:
                        sources.append("?/p.?")

                human_content = f"## Context\n{docs}\n\n##Question#{user_input}"
            else:
                human_content = user_input
                sources = []

            for reply in chat_llm.ask(human_content):
                print(reply, end="", flush=True)

            # RAG 사용 시 출처 표시
            if is_rag and sources:
                print("\n\n📄 출처:")
                for source in sources:
                    print(f"  - {source}")
            print()

        except (KeyboardInterrupt, EOFError):
            print('\n\n👋 Goodbye!')
            break


if __name__ == '__main__':
    main()
```

## 요약

=== "서비스 준비 단계"

    ``` sh
    # 1) 라이브러리 설치
    pip install -U 'django-pyhub-rag[all]'
    
    # 2) API Key 설정 (.env)
    UPSTAGE_API_KEY=...
    OPENAI_API_KEY=...
    
    # 3) Document Parse API를 통해 jsonl 파일 생성
    python -m pyhub.parser upstage -i ./doc.pdf  # pptx 등
    
    # 4) VectorDocument 모델 생성 및 마이그레이션
    
    # 5) 지정 VectorDocument로 데이터 저장 및 임베딩
    python manage.py load_jsonl myrag.VectorDocument ./output/doc.jsonl
    ```

=== "서비스 단계"
    
    ``` python
    from myrag.models import VectorDocument
    
    # 유사 문서 검색
    user_input = "..."
    docs = VectorDocument.objects.similarity_search(user_input)
    human_content = f"## Context\n{docs}\n\n##Question#{user_input}"
    
    from pyhub.llm import OpenAILLM
    
    llm = OpenAILLM(model="gpt-4o")
    reply = llm.ask(human_content)
    print(reply.text)
    print(reply.usage)
    ```
