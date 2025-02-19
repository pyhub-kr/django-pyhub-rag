# django-pyhub-rag

> **Note**: 이 라이브러리는 현재 베타버전입니다. 기능이 변경될 수 있으며, 피드백을 환영합니다.

## 소개

`django-pyhub-rag`는 장고 프로젝트에서 RAG (Retrieval Augmented Generation) 기능을 쉽게 구현할 수 있도록 도와주는 라이브러리입니다.

PostgreSQL 데이터베이스의 `pgvector` 확장을 활용하여 유사도 기반 조회를 지원합니다.

* 참고: [pgvector 설치가이드](https://ai.pyhub.kr/setup/vector-stores/pgvector/)

## 주요 기능

`AbstractDocument` 모델은 텍스트 문서와 해당 문서의 임베딩 벡터를 저장하고 관리하는 추상 기본 모델입니다.
이 모델을 상속받아 사용자 정의 문서 모델을 쉽게 구현할 수 있습니다.

```python
from pyhub.rag.models import AbstractDocument
from pgvector.django import HnswIndex

class TaxlawDocument(AbstractDocument):
    class Meta:
        indexes = [
            HnswIndex(
                name="taxlaw_doc_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
```

`AbstractDocument` 모델의 `objects` 모델 매니저로서 `DocumentQuerySet`이 지정되어있고,
유사 문서 검색을 위한 `search` 메서드를 지원합니다.

```python
doc_list = await TaxlawDocument.objects.search("질의 내용")
지식: str = str(doc_list)

# LLM 프롬프트에 `지식` 문자열 활용하여 RAG 수행
```

## 설치 요구사항

- Python 3.10+
- Django 4.0+
- PostgreSQL + pgvector 확장
- psycopg2 라이브러리 (쉬운 설치를 위해서 `psycopg2-binary` 라이브러리 추천)

## 설치 방법

1. 라이브러리 설치

```bash
pip install django-pyhub-rag
```

2. `INSTALLED_APPS` 리스트에 추가:

```python
INSTALLED_APPS = [
    # ...
    "pyhub.rag",
]
```

3. 마이그레이션을 실행하여 Vector 확장 활성화

```bash
python manage.py migrate rag
```

## 주의사항

- PostgreSQL에 pgvector 확장이 설치되어 있어야 합니다.
- 임베딩 벡터의 차원은 기본적으로 OpenAI의 `text-embedding-3-small` 모델 기준인 1536입니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
