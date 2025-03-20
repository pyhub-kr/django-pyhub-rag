# Vector Document

!!! warning

    작성 중 입니다.

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
