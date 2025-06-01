"""자동 벡터 백엔드 감지 유틸리티."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def detect_vector_backend(database_alias: str = "default") -> str:
    """
    Django 데이터베이스 설정에서 적절한 벡터 백엔드를 자동 감지합니다.
    
    Args:
        database_alias: Django DATABASES 설정의 데이터베이스 별칭
        
    Returns:
        감지된 백엔드 이름 ('pgvector' 또는 'sqlite-vec')
        
    Raises:
        ValueError: 지원하지 않는 데이터베이스 엔진인 경우
        ImportError: Django가 설정되지 않은 경우
    """
    try:
        from django.conf import settings
        
        if not settings.configured:
            raise ImportError("Django settings not configured")
            
        # 데이터베이스 설정 확인
        if database_alias not in settings.DATABASES:
            raise ValueError(f"Database alias '{database_alias}' not found in DATABASES setting")
            
        database_config = settings.DATABASES[database_alias]
        engine = database_config.get('ENGINE', '')
        
        logger.debug(f"Detected database engine: {engine}")
        
        # PostgreSQL 계열 감지
        if 'postgresql' in engine.lower():
            logger.debug("Using pgvector backend for PostgreSQL")
            return 'pgvector'
            
        # SQLite 계열 감지
        elif 'sqlite' in engine.lower():
            logger.debug("Using sqlite-vec backend for SQLite")
            return 'sqlite-vec'
            
        else:
            raise ValueError(
                f"Unsupported database engine: {engine}. "
                f"Supported engines: postgresql, sqlite"
            )
            
    except ImportError as e:
        logger.warning(f"Django not available: {e}")
        raise ImportError(
            "Django is required for automatic backend detection. "
            "Please specify backend explicitly or configure Django settings."
        )


def get_database_config(database_alias: str = "default") -> dict:
    """
    Django 데이터베이스 설정을 반환합니다.
    
    Args:
        database_alias: Django DATABASES 설정의 데이터베이스 별칭
        
    Returns:
        데이터베이스 설정 딕셔너리
    """
    try:
        from django.conf import settings
        
        if not settings.configured:
            raise ImportError("Django settings not configured")
            
        if database_alias not in settings.DATABASES:
            raise ValueError(f"Database alias '{database_alias}' not found in DATABASES setting")
            
        return settings.DATABASES[database_alias]
        
    except ImportError:
        raise ImportError("Django is required to access database configuration")


def create_backend_config(database_alias: str = "default") -> dict:
    """
    Django 데이터베이스 설정에서 벡터 백엔드 설정을 생성합니다.
    
    Args:
        database_alias: Django DATABASES 설정의 데이터베이스 별칭
        
    Returns:
        벡터 백엔드 설정 딕셔너리
    """
    db_config = get_database_config(database_alias)
    backend = detect_vector_backend(database_alias)
    
    config = {}
    
    if backend == 'pgvector':
        # PostgreSQL 설정을 pgvector 설정으로 변환
        if 'HOST' in db_config and 'PORT' in db_config:
            host = db_config['HOST'] or 'localhost'
            port = db_config['PORT'] or 5432
            name = db_config['NAME']
            user = db_config['USER']
            password = db_config['PASSWORD']
            
            config['database_url'] = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        elif 'database_url' in db_config:
            config['database_url'] = db_config['database_url']
        else:
            raise ValueError("PostgreSQL database configuration incomplete")
            
    elif backend == 'sqlite-vec':
        # SQLite 설정을 sqlite-vec 설정으로 변환
        if 'NAME' in db_config:
            config['db_path'] = db_config['NAME']
        else:
            raise ValueError("SQLite database configuration incomplete")
            
    return config


def is_backend_available(backend_name: str) -> bool:
    """
    지정된 백엔드가 사용 가능한지 확인합니다.
    
    Args:
        backend_name: 확인할 백엔드 이름
        
    Returns:
        백엔드 사용 가능 여부
    """
    try:
        from .backends import get_backend_class
        
        backend_class = get_backend_class(backend_name)
        
        # 임시 인스턴스 생성하여 availability 확인
        if backend_name == 'pgvector':
            temp_config = {'database_url': 'postgresql://test:test@localhost/test'}
        else:  # sqlite-vec
            temp_config = {'db_path': ':memory:'}
            
        temp_instance = backend_class(temp_config)
        return temp_instance.is_available()
        
    except Exception as e:
        logger.debug(f"Backend {backend_name} not available: {e}")
        return False