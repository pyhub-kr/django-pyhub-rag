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
ElementCategoryType = Literal[
    "paragraph",
    "table",
    "figure",
    "header",
    "footer",
    "caption",
    "equation",
    "heading1",
    "list",
    "index",
    "footnote",
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
                file = base64_to_file(self.b64_str, filename=str(self.id))
            except ValueError as e:
                logger.error(f"Base64 데이터를 파일로 변환하는 중 오류 발생: {e}")
            else:
                rel_path = f"{self.category}/{file.name}"
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

        if self.image_descriptions:
            kwargs["image_descriptions"] = self.image_descriptions

        return Document(
            page_content=page_content,
            metadata={
                "id": self.id,
                "page": self.page,
                "total_pages": self.total_pages,
                "category": self.category,
                "coordinates": self.coordinates,
                "api": self.api,
                "model": self.model,
                **kwargs,
            },
            files=self.files,
            elements=self.elements,
            variants={
                DocumentFormatEnum.MARKDOWN: self.content.markdown,
                DocumentFormatEnum.HTML: self.content.html,
                DocumentFormatEnum.TEXT: self.content.text,
            },
        )
