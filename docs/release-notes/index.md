# 릴리즈 노트

## 1.4.0

🚀 **RAG 시스템 대폭 단순화 및 자동 감지 기능**

### 주요 신기능
+ **Django 설정 기반 자동 백엔드 감지**: PostgreSQL → pgvector, SQLite → sqlite-vec 자동 선택
+ **단순화된 팩토리 API**: `get_vector_store()` 자동 감지, `create_sqlite_store()`, `create_postgres_store()` 추가
+ **새로운 간단한 CLI 명령어**: `pyhub.rag create`, `pyhub.rag search`, `pyhub.rag load`
+ **Zero Configuration**: Django 프로젝트에서 추가 설정 없이 RAG 사용 가능

### CLI 개선사항  
+ 기존 명령어에서 `--backend` 파라미터 옵셔널화
+ 명령어 길이 평균 50% 단축
+ 더 직관적인 사용법: `pyhub.rag search "query" docs`

### Breaking Changes
⚠️ **VectorStoreRegistry Deprecation**: `VectorStoreRegistry`는 더 이상 사용되지 않으며 향후 버전에서 제거 예정
+ `pyhub.rag.registry` 모듈의 모든 함수에 deprecation 경고 추가
+ 기존 코드는 경고와 함께 계속 동작하지만 새로운 API로 마이그레이션 권장

### 마이그레이션
+ 상세한 마이그레이션 가이드 (`MIGRATION_GUIDE.md`) 제공
+ 기존 코드 호환성 유지로 점진적 마이그레이션 가능

### 개발자 경험 향상
+ **Before**: `pyhub.rag create-collection docs --backend sqlite-vec`
+ **After**: `pyhub.rag create docs` (자동 감지)

## 1.2.2

+ `pyhub.mcp` 앱을 통한 MCP API 지원

## 1.2.1

+ `pyhub.web` 앱에서 기본 User 모델 커스텀
+ 커스텀 `404`, `500` 템플릿 지원

## 1.2.0

+ `pyhub.web`, `pyhub.ui` 앱을 통한 웹 UI 지원
+ `PGVectorDocument` 모델에서 check 프레임워크를 통해 인덱스 미지정 확인
+ `StatusMixin` 추상화 모델 클래스 추가 : 문서 처리 상태를 관리
+ `PDFFileField` 모델 필드 추가
+ `pyhub.rag` : PGVectorField 마이그레이션 시에 api key가 포함되는 버그 해결
+ `pyhub.web` 명령에서 django/uvicorn 서버 모두에서 `DEBUG=False` 상황에서도 static/media 파일 서빙 지원
+ `pyhub.web` 명령 추가 : `print-settings` (Feat. `django-extensions`)
+ `pyhub.web` 명령 추가 : migrate, showmigrations, createsuperuser, createuser, sqlmigrate, shell
+ `*_DATABASE_URL` 패턴의 환경변수를 파싱하여, `settings.DATABASES` 에 자동 등록
+ sqlite vec0, postgres pgvector 확장 설치 여부를 check 프레임워크를 통해 자동 확인
+ 새 버전이 있을 때, 표준출력으로 알림
+ `pyhub.llm ask` 명령에서 중복된 `-m` 옵션 제거 (버그)

## 1.1.4

+ 단일 Element를 Document로 변환할 때, elements 속성이 누락되는 버그 해결

## 1.1.3

+ `pyhub.llm ask` 명령에 `--multi` 멀티턴 옵션 추가
+ `pyhub.llm embed` 명령에 `--verbose` 시에만 설정 내역 출력

## 1.1.2

+ 이미지 설명 작성 명령 추가 : `pyhub.llm describe 이미지파일경로`

## 1.1.1

+ 파이썬 3.12 미만에서 중첩된 f-string을 지원하지 않는 버그 해결

## 1.1.0

+ `~/.pyhub.toml`을 통한 환경변수 설정 및 이미지/테이블 설명 작성 프롬프트 커스텀 지원
+ `pyhub toml -c` 명령으로 `~/.pyhub.toml` 파일 생성 지원

## 1.0.7

+ `--pages` 옵션 지원 : 지정 페이지 번호만 변환 지원 (예: `--pages 1,3,5`)
+ 시작페이지 번호 `+1` 버그 해결
+ cli 도움말 로직 개선

## 1.0.6

+ `metadata['page']`에 전체 페이지 주소를 반영

## 1.0.5

+ `pyhub.parser upstage` 명령 : `metadata["source"]` 항목에 PDF 파일명 추가

## 1.0.4

+ `openai`, `google`, `ollama` embed api에 대한 캐싱 지원

## 1.0.3

+ 이미지 파일명 패턴 변경
    - 기존 : `category/id.jpg`
    - 변경 : `p페이지번호/id-category.jpg`

![](./assets/1.0.3.png)

## 1.0.2

+ `--batch-page-size` 옵션(`-b`)을 다시 살려서, PDF 파일을 지정 단위로 끊어서 업스테이지 Document Parse API를 호출합니다.

## 1.0.1

+ API 벤더 (upstage, openai, anthropic, google, ollama) 별로 캐시 스토리지를 분리하여, 최대 개수를 API 별로 관리합니다.
  캐싱된 개수가 5,000개가 되면 1/5이 제거됩니다.
+ `pyhub.parser upstage --cache-clear-all` 옵션으로 모든 캐시를 초기화합니다.