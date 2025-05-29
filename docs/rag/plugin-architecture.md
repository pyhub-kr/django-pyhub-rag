# RAG Vector Store 플러그인 아키텍처

## 개요

PyHub RAG는 플러그인 기반 아키텍처를 통해 다양한 벡터 스토어 백엔드를 지원합니다. 현재 PostgreSQL pgvector와 SQLite-vec를 지원하며, 향후 더 많은 백엔드를 추가할 수 있도록 설계되었습니다.

## 아키텍처 구조

### 주요 컴포넌트

1. **BaseVectorStore**: 모든 백엔드가 구현해야 하는 추상 기본 클래스
2. **Backend Implementations**: 각 벡터 스토어별 구현체
3. **Registry System**: 백엔드 관리 및 설정 로딩
4. **Unified CLI**: 통합된 명령행 인터페이스

### 디렉토리 구조

```
pyhub/rag/
├── backends/
│   ├── __init__.py      # 백엔드 레지스트리
│   ├── base.py          # 추상 기본 클래스
│   ├── pgvector.py      # PostgreSQL pgvector 구현
│   └── sqlite_vec.py    # SQLite-vec 구현
├── registry.py          # 설정 관리 및 백엔드 생성
├── cli.py              # 통합 CLI 인터페이스
└── commands/           # 레거시 백엔드별 명령 (하위 호환성)
```

## BaseVectorStore 인터페이스

모든 벡터 스토어 백엔드는 다음 메서드를 구현해야 합니다:

### 필수 메서드

```python
class BaseVectorStore(ABC):
    @abstractmethod
    def create_collection(self, name: str, dimension: int, distance_metric: str = "cosine", **kwargs) -> None:
        """벡터 컬렉션을 생성합니다."""
        
    @abstractmethod
    def insert(self, collection_name: str, documents: List[Document], batch_size: int = 1000) -> int:
        """문서들을 컬렉션에 삽입합니다."""
        
    @abstractmethod
    def search(self, collection_name: str, query_embedding: List[float], k: int = 10, 
               filter: Optional[Dict[str, Any]] = None, threshold: Optional[float] = None) -> List[SearchResult]:
        """유사도 검색을 수행합니다."""
        
    @abstractmethod
    def is_available(self) -> bool:
        """백엔드가 사용 가능한지 확인합니다."""
```

### 데이터 모델

```python
@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

@dataclass
class SearchResult:
    document: Document
    score: float  # 유사도 점수 (0-1, 1이 가장 유사)
```

## 설정 관리

### TOML 설정 파일

`~/.pyhub.toml` 파일에서 벡터 스토어 설정을 관리합니다:

```toml
[rag]
# 기본 벡터 스토어 백엔드
default_backend = "sqlite-vec"

[rag.backends.pgvector]
enabled = true
database_url = "postgresql://user:pass@localhost:5432/vectordb"
default_dimensions = 1536
index_type = "hnsw"
distance_metric = "cosine"

[rag.backends.sqlite-vec]
enabled = true
db_path = "~/.pyhub/vector.db"
default_dimensions = 1536
distance_metric = "cosine"
```

### 설정 우선순위

1. CLI 명령행 옵션
2. 환경변수
3. TOML 설정 파일
4. 기본값

## CLI 사용법

### 통합 명령어

```bash
# 사용 가능한 백엔드 확인
pyhub.rag list-backends

# 컬렉션 생성 (기본 백엔드 사용)
pyhub.rag create-collection mytable

# 특정 백엔드로 컬렉션 생성
pyhub.rag create-collection mytable --backend pgvector

# JSONL 파일 임포트
pyhub.rag import-jsonl data.jsonl --collection mytable

# 유사도 검색
pyhub.rag similarity-search "검색할 텍스트" --collection mytable

# 통계 확인
pyhub.rag stats mytable
```

### 레거시 명령어 (하위 호환성)

기존 사용자를 위해 백엔드별 명령도 계속 지원됩니다:

```bash
pyhub.rag pgvector create-table mytable
pyhub.rag sqlite-vec create-table mytable
```

## 백엔드 구현 가이드

### 1. 새 백엔드 클래스 생성

```python
# pyhub/rag/backends/my_backend.py
from .base import BaseVectorStore

class MyVectorStore(BaseVectorStore):
    def _validate_config(self) -> None:
        # 설정 검증 로직
        pass
    
    def is_available(self) -> bool:
        # 백엔드 사용 가능 여부 확인
        pass
    
    # 나머지 필수 메서드 구현...
    
    @property
    def backend_name(self) -> str:
        return "my-backend"
    
    @property
    def required_dependencies(self) -> List[str]:
        return ["my-vector-lib"]
```

### 2. 백엔드 등록

```python
# pyhub/rag/backends/__init__.py
_BACKENDS: Dict[str, str] = {
    "pgvector": "pyhub.rag.backends.pgvector.PgVectorStore",
    "sqlite-vec": "pyhub.rag.backends.sqlite_vec.SqliteVecStore",
    "my-backend": "pyhub.rag.backends.my_backend.MyVectorStore",  # 추가
}
```

### 3. TOML 템플릿 업데이트

`pyhub/core/toml_utils.py`의 `get_default_toml_content()` 함수에 새 백엔드 설정 섹션을 추가합니다.

## Python API 사용법

### 기본 사용법

```python
from pyhub.rag import get_vector_store, Document

# 기본 백엔드 사용
store = get_vector_store()

# 특정 백엔드 사용
store = get_vector_store("pgvector")

# 설정 오버라이드
store = get_vector_store("pgvector", database_url="postgresql://...")

# 컬렉션 생성
store.create_collection("my_docs", dimension=1536)

# 문서 삽입
docs = [
    Document(
        page_content="샘플 텍스트",
        metadata={"source": "doc1.pdf"},
        embedding=[0.1, 0.2, ...]  # 1536차원
    )
]
store.insert("my_docs", docs)

# 검색
results = store.search("my_docs", query_embedding, k=5)
for result in results:
    print(f"Score: {result.score}")
    print(f"Content: {result.document.page_content}")
```

### 고급 사용법

```python
from pyhub.rag import VectorStoreRegistry

# 커스텀 레지스트리 생성
registry = VectorStoreRegistry(toml_path="/custom/path.toml")

# 사용 가능한 백엔드 확인
available = registry.list_available_backends()

# 백엔드 설정 가져오기
config = registry.get_backend_config("pgvector")
```

## 성능 고려사항

### 배치 처리

대량의 문서를 처리할 때는 적절한 배치 크기를 사용하세요:

```python
# 좋은 예
store.insert("collection", documents, batch_size=1000)

# 나쁜 예 (메모리 과다 사용)
store.insert("collection", documents, batch_size=100000)
```

### 인덱싱

- **pgvector**: HNSW 인덱스는 검색 속도가 빠르지만 생성 시간이 오래 걸립니다
- **sqlite-vec**: 자동 인덱싱으로 별도 설정이 필요 없습니다

### 거리 메트릭

- **cosine**: 정규화된 벡터에 적합 (기본값)
- **l2**: 유클리드 거리, 절대적 거리가 중요한 경우
- **inner_product**: 내적, 특수한 경우에 사용

## 문제 해결

### 백엔드를 찾을 수 없음

```bash
pyhub.rag list-backends
```

위 명령으로 사용 가능한 백엔드를 확인하고 필요한 의존성을 설치하세요.

### pgvector 설치

```bash
# PostgreSQL 확장 설치
CREATE EXTENSION vector;

# Python 패키지 설치
pip install psycopg2-binary pgvector
```

### sqlite-vec 설치

```bash
pip install sqlite-vec
```

## 향후 계획

- ChromaDB, Pinecone, Weaviate 등 추가 백엔드 지원
- 벡터 스토어 간 마이그레이션 도구
- 하이브리드 검색 (벡터 + 키워드) 지원
- 멀티테넌시 지원