# django-pyhub-rag

> **Note**: 이 라이브러리는 현재 베타버전입니다. 기능이 변경될 수 있으며, 피드백을 환영합니다.

## 소개

`django-pyhub-rag`는 장고 프로젝트에서 RAG (Retrieval Augmented Generation) 기능을 쉽게 구현할 수 있도록 도와주는 라이브러리입니다.

PostgreSQL 데이터베이스의 `pgvector` 확장을 활용하여 유사도 기반 조회를 지원합니다.

* 참고: [pgvector 설치가이드](https://ai.pyhub.kr/setup/vector-stores/pgvector/)

## 주요 기능

`sqlite-vec`와 `pgvector` 라이브러리를 지원합니다.

* `SQLiteDocument` 모델 상속을 통해 `sqlite-vec` 기반으로 텍스트 문서와 메타데이터, 임베딩 벡터를 저장하고, 유사 문서를 검색할 수 있습니다.
* `PostgresDocument` 모델 상속을 통해 `pgvector` 기반으로 텍스트 문서와 메타데이터, 임베딩 벡터를 저장하고, 유사 문서를 검색할 수 있습니다.

```python
from pyhub.rag.models.sqlite import SQLiteDocument


class TaxlawDocument(SQLiteDocument):
    pass
```

## 설치 방법

1. 라이브러리 설치

`sqlite-vec` 확장을 사용하실 경우, 아래 라이브러리를 설치해주세요.

```
python -m pip install django-pyhub-rag sqlite-vec
```

`pgvector` 확장을 사용하실 경우, 아래 라이브러리를 설치해주세요.

```
python -m pip install django-pyhub-rag psycopg2-binary pgvector
```

2. `INSTALLED_APPS` 리스트에 추가:

```python
INSTALLED_APPS = [
    # ...
    "pyhub.rag",
]
```

3. 모델 상속 및 마이그레이션

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

