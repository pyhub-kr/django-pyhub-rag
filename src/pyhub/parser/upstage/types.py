import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from re import search, sub
from typing import Literal, Union

from django.core.files import File

from pyhub.parser.documents import Document
from pyhub.parser.utils import base64_to_file

logger = logging.getLogger(__name__)


# Type aliases
DocumentSplitStrategyType = Literal["page", "element", "none"]
OCRModeType = Literal["force", "auto"]
DocumentFormatType = Literal["markdown", "html", "text"]

# 공간 정보 (spacing, position)와 스타일 정보(font size, font style)dmf ghkfdydgo
ElementCategoryType = Literal[
    # 문서에서 가장 중요한 텍스트 단락으로, 본문 내용을 구성하는 핵심적인 요소
    "paragraph",
    # 행과 열과 데이터를 구성해 정보를 한눈에 비교/분석하도록 정리하는 요소
    "table",
    # 다이어그램, 그림, 사진 등 시각 자료를 담고 있는 요소
    "figure",
    # 각 페이지 상단에 위치해, 문서 식별자나 제목 등 반복 표시가 필요한 정보를 담는 영역
    "header",
    # 문서 하단에 배치해 페이지 번호나 문서 제목 같은 반복 정보를 표시하는 영역
    "footer",
    # 표나 그림 등 시각적 요소에 대한 설명을 제공하는 텍스트 영역
    "caption",
    # 블럭 형태의 수식이나 수학적 표현을 표시하는 영역
    "equation",
    # 문서 내 주요 섹션이나 페이지 제목 등, 구조를 구분하기 위해 큰 제목으로 사용되는 요소
    "heading1",
    # 불릿 포인트나 번호를 활용해 텍스트를 목록 형태로 구성해, 정보를 더 구조적으로 정리하고 읽기 쉽게 만드는 요소
    "list",
    # 문서 전체의 목차나 참조 목록처럼, 특정 버로를 빠릐게 찾을 수 있도록 모아두는 요소
    "index",
    # 본문과 연계되는 주석이나 참고 자료 등을 페이지 하단에 별도로 표기하는 요소
    "footnote",
    # bar, pie, line 차트 형태로 데이터를 시각화해 표현하는 요소
    "chart",
]


# Enum classes
class DocumentSplitStrategyEnum(str, Enum):
    PAGE = "page"
    ELEMENT = "element"
    NONE = "none"


class OCRModeEnum(str, Enum):
    FORCE = "force"
    AUTO = "auto"


class DocumentFormatEnum(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"

    @classmethod
    def to_ext(cls, value: "DocumentFormatEnum") -> str:
        if value == cls.MARKDOWN:
            return ".md"
        elif value == cls.HTML:
            return ".html"
        elif value == cls.TEXT:
            return ".txt"
        return ".txt"


class CategoryEnum(str, Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    HEADER = "header"
    FOOTER = "footer"
    CAPTION = "caption"
    EQUATION = "equation"
    HEADING1 = "heading1"
    LIST = "list"
    INDEX = "index"
    FOOTNOTE = "footnote"
    CHART = "chart"


@dataclass
class Coordinate:
    x: float
    y: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ElementContent:
    markdown: str
    html: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)

    def __add__(self, other: Union["ElementContent", str]) -> "ElementContent":
        if isinstance(other, str):
            return ElementContent(
                markdown=self.markdown + other,
                html=self.html + other,
                text=self.text + other,
            )
        elif isinstance(other, ElementContent):
            return ElementContent(
                markdown=self.markdown + other.markdown,
                html=self.html + other.html,
                text=self.text + other.text,
            )
        else:
            raise NotImplementedError

    def __radd__(self, other: Union[str, int]) -> "ElementContent":
        if other == 0 or other == "":
            return self
        elif isinstance(other, str):
            return ElementContent(markdown=other + self.markdown, html=other + self.html, text=other + self.text)
        else:
            return NotImplemented


@dataclass
class Element:
    id: int
    page: int
    total_pages: int
    category: ElementCategoryType
    content: ElementContent
    b64_str: str
    coordinates: list[Coordinate]
    api: str
    model: str
    # API 응답에서 Element 마다 base64 파일은 1개이지만, Element가 합쳐지면 2개 이상이 될 수 있기에 dict 타입으로 지정했습니다.
    files: dict[str, File] = field(default_factory=dict)
    separator: str = "\n\n"
    elements: list["Element"] = field(default_factory=list)
    image_descriptions: str = ""

    def __post_init__(self):
        if self.b64_str:
            try:
                file = base64_to_file(self.b64_str, filename=f"{self.id:02}-{self.category}")
            except ValueError as e:
                logger.error(f"Base64 데이터를 파일로 변환하는 중 오류 발생: {e}")
            else:
                rel_path = f"p{self.page:03}/{file.name}"
                self.files[rel_path] = file

                # HTML: img 태그에 src 속성 추가하고 파일 상대경로 지정
                if search(r"<\s*img", self.content.html):
                    self.content.html = sub(r"<img ", f'<img src="{rel_path}" ', self.content.html)

                # MARKDOWN: 이미지 플레이스홀더에 파일 상대경로 적용
                if "![" in self.content.markdown:
                    self.content.markdown = sub(r"!\[(.*?)\]\((?:.*?)\)", f"![\\1]({rel_path})", self.content.markdown)

                # TEXT : image 없음.

                self.b64_str = ""

    def __add__(self, other: "Element") -> "Element":
        if self.api != other.api or self.model != other.model:
            raise ValueError("Cannot add elements with different API or model")

        # Accumulate elements
        accumulated_elements = []
        if self.elements:
            accumulated_elements.extend(self.elements)
        else:
            accumulated_elements.append(self)

        if other.elements:
            accumulated_elements.extend(other.elements)
        else:
            accumulated_elements.append(other)

        # Merge files dictionaries
        merged_files = dict(self.files)
        merged_files.update(other.files)

        return Element(
            id=self.id,  # Keep the first element's ID
            page=self.page,  # Keep the first element's page
            total_pages=self.total_pages,  # keep the first element's page
            category=self.category,  # Keep the first element's category
            content=self.content + self.separator + other.content,
            b64_str=self.b64_str,  # Keep the first element's b64_str
            coordinates=self.coordinates + other.coordinates,
            api=self.api,
            model=self.model,
            files=merged_files,  # Add merged files dictionary
            separator=self.separator,
            elements=accumulated_elements,  # Add accumulated elements
            image_descriptions=(self.image_descriptions + self.separator + other.image_descriptions).strip(),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_document(self, document_format: DocumentFormatType = "markdown", **kwargs) -> Document:
        page_content = getattr(
            self.content,
            document_format,
            f"Invalid document_format : {document_format}",
        )

        if self.coordinates:
            kwargs["coordinates"] = self.coordinates

        if self.image_descriptions:
            kwargs["image_descriptions"] = self.image_descriptions

        # elements가 비어있으면 현재 element를 포함
        elements = self.elements if self.elements else [self]

        return Document(
            page_content=page_content,
            metadata={
                "id": self.id,
                "page": self.page,
                "total_pages": self.total_pages,
                "category": self.category,
                "api": self.api,
                "model": self.model,
                **kwargs,
            },
            files=self.files,
            elements=elements,  # 수정된 elements 사용
            variants={
                DocumentFormatEnum.MARKDOWN: self.content.markdown,
                DocumentFormatEnum.HTML: self.content.html,
                DocumentFormatEnum.TEXT: self.content.text,
            },
        )
