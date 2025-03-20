# django-pyhub-rag

> **Note**: 이 라이브러리는 현재 베타버전입니다. 기능이 변경될 수 있으며, 다양한 피드백을 환영합니다.

## 소개

`django-pyhub-rag`는 장고 프로젝트에서 RAG (Retrieval Augmented Generation) 기능을 손쉽게 구현할 수 있도록 도와주는 라이브러리입니다.

**윈도우/맥/리눅스 모두 지원**

## 주요 기능

1. `pyhub.parser upstage` 명령을 통해 손쉽게 PDF 문서를 jsonl 문서로 파싱할 수 있습니다. 이미지/표를 이미지로 추출가능하며, `--enable-image-descriptor` (`-i`) 옵션 지정 만으로 `openai`, `anthropic`, `google`, `ollama` 등의 다양한 모델을 통해 이미지 설명을 생성할 수 있습니다.
2. 동일 `upstage`/`openai`/`anthropic`/`google`/`ollama` api 요청을 최대 5,000개까지 캐싱하여 (장고 캐시 프레임워크 활용), 동일 API 요청에 대해 캐싱하여 API 요금을 절감합니다.
    - 디폴트 로컬에 파일로 캐싱되며, 손쉽게 설정 만으로 외부 redis/db 서버를 캐시 서버로 쓸 수 있습니다. 그러면 다른 유저와 캐싱된 API 응답을 공유할 수 있습니다. (옵션 제공 예정)
3. 장고 모델에 손쉽게 Vector Store 기능을 통합할 수 있습니다. 내부적으로 `pgvector` 라이브러리와 `sqlite-vec` 라이브러리를 활용합니다.

    - 유사도 기반 조회를 지원합니다.
    - `pyhub.parser upstate` 명령으로 생성된 Document jsonl 파일을 장고 모델로 구성된 Vector Store에 저장한 후에 즉시 RAG 채팅을 구현할 수도 있습니다.
    - 참고: [pgvector 설치가이드](https://ai.pyhub.kr/setup/vector-stores/pgvector/)

> 장고로 만들어진 유틸리티 혹은 API 서버를 AI 에이전트 시스템을 위한 데이터 전처리 전용 웹서비스로 만드시는 것은 어떠신가요?
> 랭체인, 라마인덱스, 스프링 등의 서비스에서 손쉽게 변환된 데이터를 가져가실 수 있습니다.
> `django-pyhub-rag` 라이브러리와 함께 만들어가보시죠. 😉

## TODO

* [ ] 공식 문서 사이트 개설
* [ ] 이미지 생성 프롬프트 커스텀 지원
* [ ] API 캐싱을 API 벤더 별로 분리
* [ ] API 캐싱 백엔드 커스텀 지원 (Redis, DB 등)
* [ ] 명령 자동완성 지원

## 검토 중인 기능

* [ ] 자체 웹 서버 구동 기능
* [ ] 자체 GUI 구동 기능
* [ ] RAG 시스템 통합

## 1번의 명령으로 PDF로부터 문서내용/이미지/이미지설명 추출하기 

### API Key 획득 및 저장

PDF 파싱을 위해 Upstage API Key와 이미지 설명 생성을 위해 OpenAI API Key를 먼저 획득해주세요.

+ [Upstage API Key 얻기](https://console.upstage.ai/api-keys) : 가입하시면 웰컴 쿠폰으로 `$10`을 받으실 수 있습니다. 1페이지 변환에 `$0.01` 비용이 부과되므로 1,000장을 변환하실 수 있습니다.
+ [OpenAI API Key 얻기](https://platform.openai.com/api-keys)

획득하신 각 Key는 `~/.pyhub.env` (윈도우: `c:\Users\사용자명\.pyhub.env`) 경로에 저장하시면 유틸리티에서 환경변수로서 추가로 읽어갑니다. 
Upstage API Key는 `UPSTAGE_API_KEY` 이름으로 지정해주시고, OpenAI API Key는 `OPENAI_API_KEY` 이름으로 지정해주세요.
`~/.pyhub.env` 가 아니라 시스템/유저 환경변수로 등록되어있어도 동작합니다.

```
UPSTAGE_API_KEY=up_...
OPENAI_API_KEY=sk-...
```

이 외에도 Anthropic, Google API를 사용하신다면 `ANTHROPIC_API_KEY`와 `GOOGLE_API_KEY` 설정도 지원합니다.

![](./docs/assets/01_pyhub_env.png)

### 가상환경 생성 및 활성화 

다른 라이브러리와 충돌을 막기 위해, 가상환경을 먼저 생성하시고 활성화해주세요.

![](./docs/assets/02_venv.png)

### 라이브러리 설치

가상환경에 `django-pyhub-rag[parser]` 라이브러리만 설치해주시면 됩니다.

```
python -m pip install --upgrade 'django-pyhub-rag[parser]'
```

![](./docs/assets/03_package_install.png)

### 설치 확인

라이브러리가 정상적으로 설치되셨다면, 다음 3가지 방법으로 `pyhub.parser upstage` 명령을 실행하실 수 있습니다.

```
# 실행 방법 #1
python -m pyhub.parser upstage --help

# 실행 방법 #2
pyhub.parser upstage --help

# 실행 방법 #3
uv run -m pyhub.parser upstage --help
```

![](./docs/assets/04_package_install_complete.png)

그리고, 변환할 PDF 파일을 하나 준비해주세요.

+ [Argus Bitumen](https://www.argusmedia.com/en/solutions/products/argus-bitumen)는
  전 세계 비트멘(아스팔트) 시장에 대한 가격 평가, 뉴스, 시장 분석을 제공하는 주간 서비스입니다
  사이트의 Related documents 메뉴에서 Sample Report, Download now 링크를 통해 샘플 보고서를 다운받으실 수 있는 데요.
  매 페이지마다 상하단에 header/footer가 있고 **2단 컬럼** 구조이며, 표와 이미지가 포함된 복잡한 PDF 문서입니다.

### 첫 변환

PDF 파일 경로를 지정하시면 즉시 PDF 문서 파싱이 수행되고 `./output/` 경로에 jsonl 파일 및 추출된 이미지 파일이 저장됩니다.

```
pyhub.parser upstage ./argus-bitumen.pdf
```

![](./docs/assets/05_gen_1.png)

명령이 성공적으로 수행되었습니다.

![](./docs/assets/06_gen_2.png)

이때 `UPSTAGE_API_KEY`에 문제가 있다면 다음의 에러 메시지를 만나시게 됩니다.
`~/.pyhub.env` 파일에서 `UPSTAGE_API_KEY` 설정을 확인해주세요. 등호 `=` 앞 뒤로 절대 띄워쓰기를 쓰시면 안 됩니다.
혹은 `upstage` 명령에서 `--upstage-api-key` 인자로 API Key를 지정하실 수도 있습니다.

```
문서 파싱 실패: 401 - {"error":{"message":"API key is invalid, please check out our API reference page
(https://console.upstage.ai/docs/getting-started/overview)","type":"invalid_request_error","param":"","code":"invalid_api_key"}}
```

면, `output/` 폴더 경로에

+ `chart`, `figure`, `table` 폴더에 Upstage Document Parse로부터 추출된 이미지가 모두 저장되며
+ `argus-bitumen.jsonl` 경로에 Vector Store에 즉시 저장하실 수 있도록 `Document(page_content, metadata)` 포맷의 `jsonl` 파일로 생성되며,
    - 디폴트로 PDF 페이지 단위로 묶어서 `Document`가 생성되며, `--document-split-strategy` (`-s`) 옵션을 `element`로 지정하시면
      Update Document Parse에서 생성해준 Element 단위로 `Document`가 생성됩니다.
+ 그리고, 통합문서로서 `.md`, `.html`, `.md` 문서가 자동 생성되며, `.md`, `.html` 파일에는 이미지 링크가 자동으로 걸립니다.

![](./docs/assets/07_file_list_1.png)

![](./docs/assets/08_file_list_2.png)

생성된 `./output/argus-bitumen.jsonl` 파일의 `metadata`는 아래와 같습니다.

```markdown
{"page_content": "생략", "metadata": {"id": 0, "page": 1, "total_pages": 1, "category": "heading1", "coordinates": [], "api": "2.0", "model": "document-parse-250116"}}
```

### 수행내역 자세히 보기

`--verbose` 옵션을 적용하시면, 각종 설정 및 수행내역을 자세히 확인하실 수 있습니다.

![](./docs/assets/09_verbose.png)

### 이미지 설명 생성하기

`--enable-image-descriptor` (`-i`) 옵션을 추가로 지정하시면, 디폴트로 `OpenAI` `gpt-4o-mini` 모델로 이미지 설명을 생성해줍니다.
물론 `anthropic`, `google`, `ollama` 등을 통한 이미지 설명을 생성하실 수 있습니다.

```
pyhub.parser upstage -i ./argus-bitumen.pdf
```

아래 스크린샷에서 `-f` 옵션은 `output` 폴더가 있더라도 제거하고 강제로 재생성하는 옵션입니다. `-f` 옵션을 붙이지 않으면 `output` 폴더가 있을 경우
진행유무를 물어봅니다.

![](./docs/assets/10_image_descriptions.png)

`argus-bitumen.pdf` 파일에 대한 `Upstage Document Parse` API가 이미 호출했었기에,
지금 다시 명령을 수행하더라도 `Upstage Document Parse` API 호출을 다시 하지 않고, 로컬에 파일로 캐싱된 API 응답을 활용합니다.
(장고 캐시 프레임워크 활용)

각 이미지에 대해서 `OpenAI`, `gpt-4o-mini` API 호출은 처음이기에, 각 이미지 별로 `OpenAI` API 호출이 순차적으로 이뤄집니다.
수행이 끝나면 아래와 같이 각 이미지 파일과 함께 설명 파일을 확인하실 수 있습니다.

![](./docs/assets/11_file_list_1.png)

![](./docs/assets/12_file_list_2.png)

생성된 `.jsonl` 파일에서는 이렇게 이미지 링크가 설명이 잘 생성되어있음을 확인하실 수 있습니다.

![](./docs/assets/13_jsonl_image_descriptions.png)

디폴트로 로컬 머신에 `upstate`/`openai`/`anthropic`/`google`/`ollama` API 요청 내역을 캐싱합니다.
방금 수행한 `pyhub.parser upstage -i ./argus-bitumen.pdf` 명령을 다시 수행해보시면
캐싱된 내역을 사용하기에 즉시 명령이 종료되고 `output` 폴더 경로에 파일이 재생성됨을 확인하실 수 있습니다.

### help

보다 자세한 옵션은 `--help` 도움말을 참고해주세요.

![](./docs/assets/14_help.png)

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
