import tempfile
from pathlib import Path

DOCUMENT_PARSE_API_URL = "https://api.upstage.ai/v1/document-ai/document-parse"
DOCUMENT_PARSE_DEFAULT_MODEL = "document-parse"
DEFAULT_TIMEOUT = 600

# 파일 제약사항 관련 상수
SUPPORTED_FILE_EXTENSIONS = ["pdf", "jpeg", "jpg", "png", "bmp", "tiff", "tif", "heic", "docx", "pptx", "xlsx"]
MAX_FILE_SIZE_MB = 50
MAX_PIXELS_PER_PAGE = 100_000_000  # 1억 픽셀

# https://console.upstage.ai/docs/capabilities/document-parse
#  - 파일 1개당 최대 100페이지 지원. 그 이상은 비동기 API를 통해 처리 가능.
MAX_BATCH_PAGE_SIZE = 100
DEFAULT_BATCH_PAGE_SIZE = 10

CACHE_DIR_PATH = Path(tempfile.gettempdir()) / "pyhub.parser"
MAX_CACHE_SIZE_MB = 1024
