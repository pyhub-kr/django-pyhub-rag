"""단순화된 벡터 스토어 팩토리."""

import logging
from typing import Optional

from .backends import get_backend_class
from .backends.base import BaseVectorStore
from .detection import create_backend_config, detect_vector_backend

logger = logging.getLogger(__name__)


def get_vector_store(
    backend_name: Optional[str] = None,
    database_alias: str = "default",
    **override_config
) -> BaseVectorStore:
    """
    벡터 스토어 인스턴스를 생성합니다.
    
    Args:
        backend_name: 백엔드 이름 (None이면 자동 감지)
        database_alias: Django 데이터베이스 별칭
        **override_config: 추가 설정 오버라이드
        
    Returns:
        벡터 스토어 인스턴스
        
    Examples:
        # 자동 감지 (권장)
        store = get_vector_store()
        
        # 특정 백엔드 지정
        store = get_vector_store('pgvector')
        
        # 설정 오버라이드
        store = get_vector_store(db_path='/custom/path.db')
    """
    # 백엔드 자동 감지 또는 사용자 지정
    if backend_name is None:
        backend_name = detect_vector_backend(database_alias)
        logger.debug(f"Auto-detected backend: {backend_name}")
    else:
        logger.debug(f"Using specified backend: {backend_name}")
    
    # 백엔드 클래스 로드
    backend_class = get_backend_class(backend_name)
    
    # Django 설정에서 기본 설정 생성
    try:
        config = create_backend_config(database_alias)
        logger.debug(f"Created config from Django settings: {config}")
    except Exception as e:
        logger.warning(f"Could not create config from Django settings: {e}")
        config = {}
    
    # 사용자 설정으로 오버라이드
    config.update(override_config)
    
    # 인스턴스 생성
    logger.debug(f"Creating {backend_name} store with config: {config}")
    return backend_class(config)


def create_sqlite_store(db_path: Optional[str] = None, **config) -> BaseVectorStore:
    """
    SQLite 벡터 스토어를 생성합니다.
    
    Args:
        db_path: SQLite 데이터베이스 파일 경로 (None이면 Django 설정 사용)
        **config: 추가 설정
        
    Returns:
        SQLite 벡터 스토어 인스턴스
    """
    if db_path is not None:
        config['db_path'] = db_path
        
    return get_vector_store('sqlite-vec', **config)


def create_postgres_store(database_url: Optional[str] = None, **config) -> BaseVectorStore:
    """
    PostgreSQL 벡터 스토어를 생성합니다.
    
    Args:
        database_url: PostgreSQL 연결 URL (None이면 Django 설정 사용)
        **config: 추가 설정
        
    Returns:
        PostgreSQL 벡터 스토어 인스턴스
    """
    if database_url is not None:
        config['database_url'] = database_url
        
    return get_vector_store('pgvector', **config)


def list_available_backends() -> list[str]:
    """
    사용 가능한 백엔드 목록을 반환합니다.
    
    Returns:
        사용 가능한 백엔드 이름 리스트
    """
    from .backends import list_backends
    from .detection import is_backend_available
    
    available = []
    for backend_name in list_backends():
        if is_backend_available(backend_name):
            available.append(backend_name)
        else:
            logger.debug(f"Backend {backend_name} not available")
    
    return available


# 하위 호환성을 위한 별칭
create_vector_store = get_vector_store