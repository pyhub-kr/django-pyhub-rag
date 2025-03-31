from typing import Optional

from django_components import Component, register
from django_components.component import DataType


@register("modal")
class Modal(Component):
    template_name = "modal.html"

    def get_context_data(self, title: Optional[str] = None) -> DataType:
        return {"title": title}
