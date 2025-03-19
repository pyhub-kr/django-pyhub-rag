# django-pyhub-rag

> **Note**: 이 라이브러리는 현재 베타버전입니다. 기능이 변경될 수 있으며, 다양한 피드백을 환영합니다.

## 소개

`django-pyhub-rag`는 장고 프로젝트에서 RAG (Retrieval Augmented Generation) 기능을 손쉽게 구현할 수 있도록 도와주는 라이브러리입니다.

## 주요 기능

1. `pyhub.parser upstage` 명령을 통해 손쉽게 PDF 문서를 jsonl 문서로 파싱할 수 있습니다. 이미지/표를 이미지로 추출가능하며, `-i` 옵션 지정 만으로
   openai, anthropic, google 등의 다양한 모델을 통해 이미지 설명을 생성할 수 있습니다.
2. 장고 모델에 손쉽게 Vector Store 기능을 통합할 수 있습니다. 내부적으로 `pgvector` 라이브러리와 `sqlite-vec` 라이브러리를 활용합니다.

    - 유사도 기반 조회를 지원합니다.
    - 참고: [pgvector 설치가이드](https://ai.pyhub.kr/setup/vector-stores/pgvector/)

## PDF 문서 파싱 기능

PDF 파싱을 위해 Upstage API Key와 이미지 설명 생성을 위해 OpenAI API Key를 먼저 획득해주세요.

+ [Upstage API Key 얻기](https://console.upstage.ai/api-keys) : 가입하시면 웰컴 쿠폰으로 $10을 받으실 수 있습니다.
+ [OpenAI API Key 얻기](https://platform.openai.com/api-keys)

획득하신 각 Key는 `~/.pyhub.env` 경로에 저장하시면 유틸리티에서 자동으로 읽어갑니다.
Upstage API Key는 `UPSTAGE_API_KEY` 이름으로 지정해주시고, OpenAI API Key는 `OPENAI_API_KEY` 이름으로 지정해주세요.

```
UPSTAGE_API_KEY=up_...
OPENAI_API_KEY=sk-...
```

다른 라이브러리와 충돌을 막기 위해, 가상환경을 먼저 생성하시고 활성화하신 후에,
`django-pyhub-rag[parser]` 라이브러리를 설치해주세요. 

```
pip install --upgrade 'django-pyhub-rag[parser]'
```

라이브러리가 정상적으로 설치되셨다면, 다음 3가지 방법으로 `pyhub.parser upstage` 명령을 실행하실 수 있습니다.

```
# 실행 방법 #1
python -m pyhub.parser upstage --help

# 실행 방법 #2
pyhub.parser upstage --help

# 실행 방법 #3
uv run -m pyhub.parser upstage --help
```

변환할 PDF 파일을 하나 준비해주세요.

[Argus Bitumen](https://www.argusmedia.com/en/solutions/products/argus-bitumen)는
전 세계 비트멘(아스팔트) 시장에 대한 가격 평가, 뉴스, 시장 분석을 제공하는 주간 서비스입니다
사이트의 Related documents 메뉴에서 Sample Report, Download now 링크를 통해 샘플 보고서를 다운받으실 수 있는 데요.
매 페이지마다 상하단에 header/footer가 있고 **2단 컬럼** 구조이며, 표와 이미지가 포함된 복잡한 PDF 문서입니다.

PDF 파일 경로를 지정하시면 즉시 PDF 문서 파싱이 수행되고 `./output/` 경로에 jsonl 파일 및 추출된 이미지 파일이 저장됩니다.

```
pyhub.parser upstage ./argus-bitumen.pdf
```

이때 `UPSTAGE_API_KEY`에 문제가 있다면 다음의 에러 메시지를 만나시게 됩니다.
`~/.pyhub.env` 파일에서 `UPSTAGE_API_KEY` 설정을 확인해주세요. 등호 `=` 앞 뒤로 절대 띄워쓰기를 쓰시면 안 됩니다.
혹은 `upstage` 명령에서 `--upstage-api-key` 인자로 API Key를 지정하실 수도 있습니다.

```
문서 파싱 실패: 401 - {"error":{"message":"API key is invalid, please check out our API reference page
(https://console.upstage.ai/docs/getting-started/overview)","type":"invalid_request_error","param":"","code":"invalid_api_key"}}
```

생성된 `./output/argus-bitumen.jsonl` 파일의 `metadata`는 아래와 같습니다.

```markdown
{"page_content": "생략", "metadata": {"id": 0, "page": 1, "total_pages": 1, "category": "heading1", "coordinates": [], "api": "2.0", "model": "document-parse-250116"}}
```

`--enable-image-descriptor` 옵션(단축: `-i`)을 추가로 지정하시면, 디폴트로 openai gpt-4o-mini 모델로 이미지 생성을 생성해줍니다.

```
pyhub.parser upstage -i ./argus-bitumen.pdf
```

그럼 아래와 같이 `metadata` 속성에 `image_descriptions`가 추가되었음을 확인하실 수 있습니다.

```markdown
{"page_content": "생략", "metadata": {"id": 0, "page": 1, "total_pages": 1, "category": "heading1", "coordinates": [], "api": "2.0", "model": "document-parse-250116", "image_descriptions": "<image name='table/12.jpg'><title>\n비트멘 가격 현황 (2023년 3월 16-22일)\n</title>\n<details>\n이 표는 비트멘의 수출 및 국내 가격을 나타냅니다. \n- 수출 화물 가격은 지중해에서 445.43달러에서 449.77달러로, 로테르담은 482.15달러에서 487.15달러로, 발틱 지역은 470.15달러에서 474.15달러로 변동했습니다.\n- 국내 가격에서는 앤트워프가 576달러에서 587달러로, 남부 독일은 522달러에서 523달러로, 헝가리는 571달러로 보고되었습니다.\n</details>\n<entities>\n비트멘, 수출 화물 가격, 국내 가격, 지중해, 로테르담, 발틱, 앤트워프, 남부 독일, 헝가리\n</entities>\n<hypothetical_questions>\n- 비트멘 가격 상승이 건설 산업에 미치는 영향은 무엇인가요?\n- 각 지역의 가격 변동이 글로벌 시장에 미치는 영향은 어떻게 될까요?\n</hypothetical_questions></image>"}}
```

보다 자세한 옵션은 `--help` 도움말을 참고해주세요.

## Vector Store 모델

Postgres 혹은 SQLite 데이터베이스 + 장고 기반으로 임베딩 데이터를 손쉽게 저장/생성하고 조회까지 수행하실 수 있습니다.

`sqlite-vec`와 `pgvector` 라이브러리를 지원합니다.

* `SQLiteVectorDocument` 모델 상속을 통해 `sqlite-vec` 기반으로 텍스트 문서와 메타데이터, 임베딩 벡터를 저장하고, 유사 문서를 검색할 수 있습니다.
* `PGVectorDocument` 모델 상속을 통해 `pgvector` 기반으로 텍스트 문서와 메타데이터, 임베딩 벡터를 저장하고, 유사 문서를 검색할 수 있습니다.

```python
from pyhub.rag.models.sqlite import SQLiteVectorDocument

class TaxlawDocument(SQLiteVectorDocument):
    pass
```

각 모델에는 다음 3개의 모델 필드가 디폴트 생성됩니다.

* `page_content` : `models.TextField` 타입
* `metadata` : `models.JSONField` 타입
* `embedding` : 커스텀 `BaseVectorField` 타입

각 모델 인스턴스 생성 시에 `page_content`, `metadata` 필드만 지정하고 저장하면 `embedding` 필드가 자동으로 생성/저장됩니다.
물론 `bulk_create`를 통한 저장에서도 `embedding` 필드가 자동 생성/저장됩니다.

레코드 생성 이후에 쿼리셋의 `.similarity_search(검색어, k=4)` 메서드를 통해 유사 문서를 검색할 수 있습니다.

## 사용한 주요 라이브러리

+ `django`
    - 요청 유효성 검사
    - 장고 템플릿을 활용한 프롬프트 관리 및 생성
    - 로거 시스템을 통한 debug/info/error 로그 출력
    - 캐시 시스템을 통한 API 요청 캐시 (디폴트: 로컬 파일 시스템) - 캐시 백엔드를 Re
+ LLM 요청 라이브러리 : `openai`, `anthropic`, `google-genai`, `ollama`, `tiktoken`, `httpx`
+ CLI : `rich`, `typer`
+ PDF 파일 : `pypdf2` (PDF 파일여부 검증, 페이지 수 읽기, 페이지 나누기)

## 관련 튜토리얼

1. `django-pyhub-rag` 라이브러리에 대한 직접적인 활용 방법에 대해서는 [파이썬사랑방 TV](https://www.youtube.com/@pyhub-kr) 유튜브 채널에서 다양하게 다뤄보겠습니다.
2. [장고로 만드는 RAG 웹 채팅 서비스](https://ai.pyhub.kr/hands-on-lab/django-webchat-rag/) 문서에서 본 라이브러리 Vector Store 기능 활용에 대해서 다루고 있습니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
