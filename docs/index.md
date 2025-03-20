# django-pyhub-rag

`django-pyhub-rag` 라이브러리는 장고 프로젝트에서 RAG (Retrieval Augmented Generation) 기능을 손쉽게 구현할 수 있도록 도와주는 라이브러리입니다. **윈도우/맥/리눅스**를 모두 지원합니다.


## 주요 기능

### PDF 문서 파싱

+ [x] `pyhub.parser upstage` 명령 1번 만으로 PDF 문서 (샘플: [argus-bitumen.pdf](https://www.argusmedia.com/-/media/project/argusmedia/mainsite/english/documents-and-files/sample-reports/argus-bitumen.pdf?rev=7512cf07937e4e4cbb8889c87780edf7))를 파싱하여 Vector Store에 즉시 반영할 수 있는 형태로 [파일들](https://github.com/pyhub-kr/django-pyhub-rag/tree/main/samples/argus-bitumen)을 생성하실 수 있습니다.
+ [x] 이미지/표를 이미지로 추출가능하며, `--enable-image-descriptor` (`-i`) 옵션 지정 만으로
  `upstage`, `openai`, `anthropic`, `google`, `ollama` 등의 다양한 모델을 통해 이미지 설명을 생성할 수 있습니다.
+ [x] 동일 `upstage`/`openai`/`anthropic`/`google`/`ollama` api 요청을 최대 5,000개까지 캐싱하여 (장고 캐시 프레임워크 활용),
  동일 API 요청에 대해 캐싱하여 API 요금을 절감합니다. 디폴트로 로컬에 파일로 캐싱되며, 추후 옵션 설정 만으로 외부 redis/db 서버를
  캐시 서버로 쓸 수 있습니다. 그러면 다른 유저와 캐싱된 API 응답을 공유할 수 있습니다.

[명령 하나 만으로 PDF 문서 파싱하는 방법이 궁금하신가요? :wink:](./parser/upstage){ .md-button }


### 장고 모델에 Vector Store 통합

별도의 Vector Store 인프라를 구축하지 않아도 Postgres 혹은 SQLite 데이터베이스에 임베딩 데이터를 저장하여 Vector Store를 구축하실 수 있습니다. 
내부적으로 `pgvector` 라이브러리와 `sqlite-vec` 라이브러리를 활용합니다.

+ 기존의 장고 모델/View 개발방법 대로 RAG 서비스를 구축하실 수 있습니다.
+ 장고 모델 기반으로 유사도 기반 조회를 지원합니다.

!!! tip

    `pyhub.parser upstage` 명령으로 생성된 Document jsonl 파일을 장고 모델로 구성된 Vector Store에 저장한 후에 즉시 RAG 채팅을 구현할 수도 있습니다.


## 사용한 주요 라이브러리

+ `django`
    - 요청 유효성 검사
    - 장고 템플릿을 활용한 프롬프트 관리 및 생성
    - 로거 시스템을 통한 debug/info/error 로그 출력
    - 캐시 시스템을 통한 API 요청 캐시 (디폴트: 로컬 파일 시스템, 지원 가능 : Redis, 데이터베이스)
+ LLM 요청 라이브러리 : `openai`, `anthropic`, `google-genai`, `ollama`, `tiktoken`, `httpx`
+ CLI : `rich`, `typer`
+ PDF 파일 : `pypdf2` (PDF 파일여부 검증, 페이지 수 읽기, 페이지 나누기)


## TODO

* [ ] 이미지 생성 프롬프트 커스텀 지원
* [ ] API 캐싱 백엔드 커스텀 지원 (Redis, DB 등)
* [ ] 명령 자동완성 지원


## 검토 중인 기능

* [ ] 자체 웹 서버 구동 기능
* [ ] 자체 GUI 구동 기능
* [ ] RAG 시스템 통합
