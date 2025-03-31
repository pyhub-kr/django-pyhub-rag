import json
from dataclasses import dataclass
from typing import Literal, Optional

from django.template import Context, Template
from django.utils.safestring import mark_safe
from django_components import Component, register

TOAST_EVENT_NAME = "toast"


@dataclass
class ToastMessage:
    message: str
    type: Literal["default", "info", "success", "warning", "error"] = "default"
    delay: Optional[int] = None

    template = Template(
        """
<script>
(function() {
    window.dispatchEvent(new CustomEvent("{{ toast_event_name }}", {{ detail_s }}));
    document.currentScript.remove();
})();
</script>
        """
    )

    def as_html(self) -> str:
        detail_s = json.dumps({"detail": {"type": self.type, "message": self.message, "delay": self.delay}})
        return self.template.render(
            Context(
                {
                    "toast_event_name": TOAST_EVENT_NAME,
                    "detail_s": mark_safe(detail_s),
                }
            )
        )


@register("toast_container")
class ToastContainer(Component):
    template_name = "toast_container.html"

    def get_context_data(self):
        return {
            "toast_event_name": TOAST_EVENT_NAME,
        }
