import asyncio
import io
import json
import logging
import os.path
from functools import reduce
from hashlib import md5
from typing import AsyncGenerator, Generator, Optional

import httpx
from django.core.exceptions import ValidationError
from django.core.files import File
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError

from pyhub.parser.documents import Document

from .settings import (
    CACHE_DIR_PATH,
    DEFAULT_TIMEOUT,
    DOCUMENT_PARSE_API_URL,
    DOCUMENT_PARSE_DEFAULT_MODEL,
    MAX_BATCH_PAGE_SIZE,
)
from .types import (
    DocumentFormatType,
    DocumentSplitStrategyType,
    Element,
    ElementCategoryType,
    ElementContent,
    OCRModeType,
)
from .validators import validate_upstage_document

logger = logging.getLogger(__name__)


class UpstageDocumentParseParser:
    def __init__(
        self,
        upstage_api_key: Optional[str] = None,
        api_url: str = DOCUMENT_PARSE_API_URL,
        model: str = DOCUMENT_PARSE_DEFAULT_MODEL,
        split: DocumentSplitStrategyType = "page",
        max_page: int = 0,
        ocr_mode: OCRModeType = "auto",
        document_format: DocumentFormatType = "html",
        coordinates: bool = False,
        base64_encoding_category_list: Optional[list[ElementCategoryType]] = None,
        ignore_element_category_list: Optional[list[ElementCategoryType]] = None,
        ignore_cache: bool = False,
        verbose: bool = False,
    ):
        """
        UpstageDocumentParseParser 클래스의 인스턴스를 초기화합니다.

        Args:
            upstage_api_key (str, optional): Upstage API 접근을 위한 API 키.
                                     기본값은 None이며, 이 경우 환경 변수
                                     `UPSTAGE_API_KEY`에서 가져옵니다.
            api_url (str, optional): Upstage API 접근을 위한 API URL.
                                     기본값은 DOCUMENT_PARSE_API_URL입니다.
            model (str, optional): 문서 파싱에 사용할 모델.
                                  기본값은 DOCUMENT_PARSE_DEFAULT_MODEL입니다.
            split (SplitType, optional): 적용할 분할 유형.
                                         기본값은 "page"입니다.
                                         옵션:
                                         - "none": 분할 없음, 전체 문서를 단일 청크로 반환합니다.
                                         - "page": 문서를 페이지별로 분할합니다.
                                         - "element": 문서를 개별 요소(단락, 표 등)로 분할합니다.
            max_page (int, optional): 처리할 최대 페이지 수.
                                     0은 모든 페이지를 처리함을 의미합니다. 기본값은 0입니다.
            ocr_mode (OCRMode, optional): OCR을 사용하여 문서의 이미지에서 텍스트를 추출합니다.
                                     기본값은 "auto"입니다.
                                     옵션:
                                     - "force": 이미지에서 텍스트를 추출하기 위해 OCR이 사용됩니다.
                                     - "auto": PDF에서 텍스트가 추출됩니다. (입력이 PDF 형식이 아닌 경우 오류가 발생합니다)
            document_format (DocumentFormat, optional): 추론 결과의 형식.
                                                   기본값은 "html"입니다.
                                                   옵션: "text", "html", "markdown"
            coordinates (bool, optional): 출력에 OCR 좌표를 포함할지 여부.
                                          기본값은 False 입니다.
            base64_encoding_category_list (list[CategoryType], optional): base64로 인코딩할 요소의 카테고리.
                                                        기본값은 빈 리스트입니다.
            ignore_element_category_list (list[CategoryType], optional): 제외할 요소의 카테고리.
                                                        기본값은 빈 리스트입니다.
            ignore_cache (bool, optional): API 응답 캐시를 무시할지 여부.
                                         기본값은 False입니다.
            verbose (bool, optional): 상세한 처리 정보를 표시할지 여부.
                                     기본값은 False입니다.
        """
        self.upstage_api_key = upstage_api_key
        self.api_url = api_url
        self.model = model
        self.split = split
        self.max_page = max_page
        self.ocr_mode = ocr_mode
        self.document_format = document_format
        self.coordinates = coordinates
        self.base64_encoding_category_list = base64_encoding_category_list or []
        self.ignore_element_category_list = ignore_element_category_list or []
        self.validators = [validate_upstage_document]
        self.errors: Optional[list[ValidationError]] = None
        self.ignore_cache = ignore_cache
        self.verbose = verbose

    def is_valid(self, file: File, raise_exception: bool = False) -> bool:
        """
        파일이 Upstage Document Parse API 제약 조건을 충족하는지 검증합니다.
        검증이 실패하면 self.errors에 검증 오류를 수집합니다.

        Args:
            file (File): 검증할 파일 객체
            raise_exception (bool): True인 경우, 검증 실패 시 ValidationError를 발생시킵니다.
                             기본값은 False입니다.

        Returns:
            bool: 파일이 모든 검증 검사를 통과하면 True, 그렇지 않으면 False.
                  False인 경우, 검증 오류는 self.errors를 통해 접근할 수 있습니다.

        Raises:
            ValidationError: 검증이 실패하고 raise_exception이 True인 경우 발생합니다.
        """

        self.errors = []

        for validator in self.validators:
            try:
                validator(file)
            except ValidationError as e:
                self.errors.append(e)

        valid = len(self.errors) == 0

        if raise_exception and valid is False:
            raise ValidationError(self.errors)

        return valid

    def lazy_parse(
        self,
        file: File,
        batch_page_size: int,
        ignore_validation: bool = False,
    ) -> Generator[Document, None, None]:
        """
        문서를 동기적으로 파싱하고 지정된 분할 유형에 따라 Document 객체를 생성합니다.
        내부적으로는 비동기 lazy_parse 메서드를 실행하고 결과를 동기적으로 반환합니다.
        """

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async_iter = self.lazy_parse_async(file, batch_page_size, ignore_validation=ignore_validation)

        try:
            while True:
                try:
                    document = loop.run_until_complete(async_iter.__anext__())
                    yield document
                except StopAsyncIteration:
                    break
        except Exception as e:
            raise ValueError(f"동기 파싱 중 오류 발생: {e}")

    async def lazy_parse_async(
        self,
        file: File,
        batch_page_size: int,
        ignore_validation: bool = False,
    ) -> AsyncGenerator[Document, None]:
        """
        문서를 비동기적으로 파싱하고 지정된 분할 유형에 따라 Document 객체를 생성합니다.

        Args:
            file (File): 파싱할 입력 파일 객체.
            batch_page_size (int): 한 번에 처리할 페이지 수.
            ignore_validation (bool): 파일 검증을 건너뛸지 여부.
                                      기본값은 False입니다.

        Returns:
            AsyncGenerator[Document, None]: 파싱된 문서 객체들의 비동기 반복자.

        Raises:
            ValueError: 유효하지 않은 분할 유형이 제공되거나 파일 검증이 실패한 경우 발생합니다.
        """
        # 파일 유효성 검사 추가
        logger.debug("비동기 lazy_parse_async를 batch_page_size=%d로 시작합니다", batch_page_size)

        if ignore_validation is False:
            if not self.is_valid(file):
                logger.debug("파일 검증 실패: %s", self.errors)
                raise ValueError(f"파일 검증 실패: {self.errors}")
            logger.debug("파일 검증 성공")

        if self.split == "none":
            element_list = []
            async for element in self._generate_elements(file, batch_page_size):
                element_list.append(element)
            merged_element = reduce(lambda x, y: x + y, element_list)
            merged_element.coordinates = []
            document = merged_element.to_document(self.document_format)

            logger.debug(
                "문서를 %d 글자와 %d 메타데이터 항목으로 생성했습니다",
                len(document.page_content),
                len(document.metadata),
            )

            yield document

        elif self.split == "element":
            async for element in self._generate_elements(file, batch_page_size):
                yield element.to_document(self.document_format)

        elif self.split == "page":
            page_group_dict = {}
            async for element in self._generate_elements(file, batch_page_size):
                if element.page not in page_group_dict:
                    page_group_dict[element.page] = []
                page_group_dict[element.page].append(element)

            page_set: list[int] = sorted(page_group_dict.keys())

            for page in page_set:
                group: list[Element] = page_group_dict[page]
                page_element = reduce(lambda x, y: x + y, group)
                page_element.coordinates = []
                yield page_element.to_document(self.document_format)

        else:
            logger.debug("유효하지 않은 분할 유형이 제공되었습니다: %s", self.split)

            raise ValueError(f"유효하지 않은 분할 유형: {self.split}")

    async def _generate_elements(self, file: File, batch_page_size: int) -> AsyncGenerator[Element, None]:
        """
        파일을 처리하여 Element 객체들을 생성하는 비동기 제너레이터입니다.

        Args:
            file (File): 처리할 파일 객체
            batch_page_size (int): 한 번에 처리할 페이지 수

        Returns:
            AsyncGenerator[Element, None]: Element 객체들의 비동기 제너레이터

        Raises:
            ValueError: PDF 파일 읽기 실패 또는 batch_page_size가 최대 허용 페이지 수를 초과할 경우 발생합니다.
        """
        try:
            logger.debug("파일을 PDF로 읽기 시도 중")
            full_docs = PdfReader(file)
            total_pages = len(full_docs.pages)
            is_pdf = True
            logger.debug("PDF를 %d 페이지로 성공적으로 읽었습니다", total_pages)
        except PdfReadError:
            logger.debug("파일이 PDF가 아닙니다. 단일 페이지 문서로 처리합니다")
            full_docs = None
            total_pages = 1
            is_pdf = False
        except Exception as e:
            logger.debug("파일 읽기 오류: %s", str(e))
            raise ValueError(f"PDF 파일 읽기 실패: {e}")

        # max_page 제한 적용 (설정된 경우)
        if self.max_page > 0 and is_pdf:
            total_pages = min(total_pages, self.max_page)
            logger.debug("max_page 설정으로 인해 처리를 %d 페이지로 제한합니다", total_pages)

        if is_pdf:
            logger.debug("%d 페이지의 PDF 파일 처리 중", total_pages)
        else:
            logger.debug("PDF가 아닌 파일을 단일 페이지 문서로 처리 중")

        # batch_page_size가 최대 허용 페이지 수를 초과하지 않는지 검증
        if batch_page_size > MAX_BATCH_PAGE_SIZE:
            logger.debug(
                "batch_page_size (%d)가 최대 허용 페이지 수 (%d)를 초과합니다", batch_page_size, MAX_BATCH_PAGE_SIZE
            )
            raise ValueError(
                f"batch_page_size ({batch_page_size})가 최대 허용 페이지 수 ({MAX_BATCH_PAGE_SIZE})를 초과합니다"
            )

        if is_pdf:
            start_page = 0
            while start_page < total_pages:
                # 실제로 처리할 페이지 수 계산 (남은 페이지와 batch_page_size 중 작은 값)
                pages_to_process = min(batch_page_size, total_pages - start_page)

                logger.debug(
                    "%d 페이지부터 %d 페이지까지 처리 중 (총 %d 페이지)",
                    start_page,
                    start_page + pages_to_process - 1,
                    total_pages,
                )

                merger = PdfWriter()
                merger.append(
                    full_docs,
                    pages=(start_page, min(start_page + pages_to_process, len(full_docs.pages))),
                )
                with io.BytesIO() as buffer:
                    merger.write(buffer)
                    buffer.seek(0)
                    response_obj = await self._call_document_parse_api({"document": buffer})
                    async for element in self._parse_response_obj(response_obj, total_pages):
                        if element.category in self.ignore_element_category_list:
                            content_s = getattr(element.content, self.document_format)
                            content_preview = content_s[:100] + ("..." if len(content_s) > 100 else "")
                            logger.debug(
                                "Ignore element category : %s, content: %s", element.category, repr(content_preview)
                            )
                        else:
                            element.page += start_page
                            yield element

                start_page += pages_to_process

        else:
            logger.debug("PDF가 아닌 파일을 단일 페이지 문서로 처리 중")

            response_obj = await self._call_document_parse_api({"document": file})
            async for element in self._parse_response_obj(response_obj, total_pages):
                if element.category in self.ignore_element_category_list:
                    content_s = getattr(element.content, self.document_format)
                    content_preview = content_s[:100] + ("..." if len(content_s) > 100 else "")
                    logger.debug("Ignore element category : %s, content: %s", element.category, content_preview)
                else:
                    yield element

    async def _call_document_parse_api(
        self,
        files: dict,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict:
        """
        제공된 파일로 API 엔드포인트에 POST 요청을 비동기적으로 보내고 응답을 반환합니다.

        Args:
            files (dict): 요청에 보낼 파일을 포함하는 사전.
            timeout (int, optional): 요청 타임아웃(초). 기본값은 DEFAULT_TIMEOUT입니다.

        Returns:
            dict: API 응답 데이터를 포함하는 사전

        Raises:
            ValueError: API 호출에 오류가 있는 경우 발생합니다.
        """

        headers = {
            "Authorization": f"Bearer {self.upstage_api_key}",
        }
        data = {
            "ocr": self.ocr_mode,
            "model": self.model,
            "output_formats": "['html', 'text', 'markdown']",
            "coordinates": self.coordinates,
            "base64_encoding": f"{'[' + ",".join(f"'{el}'" for el in self.base64_encoding_category_list) + ']'}",
        }

        if self.ignore_cache:
            cache_path = None

        else:
            # create hash
            hasher = md5()

            for file_key in sorted(files.keys()):
                file_obj = files[file_key]
                hasher.update(file_obj.read())
                file_obj.seek(0)

            for key, value in sorted(data.items()):
                hasher.update(f"{key}={value}".encode("utf-8"))

            md5_hash_value: str = hasher.hexdigest()

            logger.debug(f"요청에 대한 MD5 해시 생성: {md5_hash_value}")

            cache_path = CACHE_DIR_PATH / f"cache-response-{md5_hash_value}.json"
            if os.path.exists(cache_path):
                logger.debug("캐싱된 API 응답이 있습니다. Upstage API를 호출하지 않고 캐싱된 API 응답을 재활용합니다.")
                json_string = open(cache_path, "rt", encoding="utf-8").read()
                return json.loads(json_string)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=timeout,
                )
                if response.status_code == 200:
                    response_obj = response.json()

                    if cache_path is not None:
                        logger.debug(f"API 응답을 캐싱합니다. 캐싱된 용량 = {len(response.text)} bytes")
                        open(cache_path, "wt", encoding="utf-8").write(response.text)

                    return response_obj
                else:
                    raise ValueError(f"문서 파싱 실패: {response.status_code} - {response.text}")
        except httpx.RequestError as e:
            raise ValueError(f"요청 전송 실패: {e}")
        except httpx.HTTPError as e:
            raise ValueError(f"HTTP 오류: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 응답 디코딩 실패: {e}")
        except Exception as e:
            raise ValueError(f"오류 발생: {e}")

    @staticmethod
    async def _parse_response_obj(response_obj: dict, total_pages: int) -> AsyncGenerator[Element, None]:
        """
        API 응답 객체를 파싱하여 Element 객체들을 생성하는 비동기 제너레이터입니다.

        Args:
            response_obj (dict): API 응답 데이터를 포함하는 사전
            total_pages (int): 문서의 총 페이지 수

        Returns:
            AsyncGenerator[Element, None]: Element 객체들의 비동기 제너레이터
        """
        api: str = response_obj.get("api")
        model: str = response_obj.get("model")
        # usage: dict = response_obj.get("usage")  # ex: { "pages": 10 }
        elements = response_obj.get("elements") or []

        logger.debug("%d개의 요소를 받았습니다", len(elements))

        for element in elements:
            yield Element(
                id=element["id"],
                page=element["page"],
                total_pages=total_pages,
                category=element["category"],
                content=ElementContent(
                    markdown=element["content"]["markdown"],
                    text=element["content"]["text"],
                    html=element["content"]["html"],
                ),
                b64_str=element.get("base64_encoding", ""),
                coordinates=element.get("coordinates") or [],
                api=api,
                model=model,
            )
