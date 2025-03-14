from dataclasses import dataclass, field
from typing import Any

from django.core.files import File


@dataclass
class Document:
    page_content: str
    metadata: dict
    files: dict[str, File] = field(default_factory=dict)
    elements: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page_content": self.page_content,
            "metadata": self.metadata,
        }
