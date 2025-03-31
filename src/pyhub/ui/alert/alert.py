import json
from dataclasses import dataclass
from typing import Any, Literal, Optional, Union

from django.http import HttpRequest, HttpResponse
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django_components import Component, registry


@dataclass
class AlertEvent:
    name: str
    params: Optional[dict[str, Any]] = None
    delay: Optional[int] = None

    template = Template(
        """
<script>
(function() {
const currentScript = document.currentScript;

{% if delay is not None %}
    setTimeout(() => {
        window.dispatchEvent(new CustomEvent("{{ name }}", {{ detail_s }}));
        currentScript.remove();
    }, {{ delay }});
{% else %}
    window.dispatchEvent(new CustomEvent("{{ name }}", {{ detail_s }}));
    currentScript.remove();
{% endif %}
})();
</script>
    """
    )

    def as_html(self) -> str:
        detail_s = json.dumps({"detail": self.params or {}})
        return self.template.render(
            Context(
                {
                    "name": self.name,
                    "detail_s": mark_safe(detail_s),
                    "delay": self.delay,
                }
            )
        )


class Alert(Component):
    template_file = "alert.html"
    context_data = {}

    def get_context_data(
        self,
        type: Literal["default", "info", "success", "warning", "error"] = "default",
        events: Optional[list[AlertEvent]] = None,
    ):
        return {
            "type": type,
            "events": events,
            **self.context_data,
        }

    @classmethod
    def make_html(
        cls,
        request: HttpRequest,
        message: str,
        event_name: Optional[str] = None,
        event_params: Optional[dict[str, Any]] = None,
        event: Optional[AlertEvent] = None,
        events: Optional[list[Union[AlertEvent, str]]] = None,
    ) -> str:
        _events: list[AlertEvent] = []

        if event_name:
            _events.append(AlertEvent(event_name, event_params))

        if event:
            _events.append(event)

        if events:
            for e in events:
                if isinstance(e, AlertEvent):
                    _events.append(e)
                elif isinstance(e, str):
                    _events.append(AlertEvent(e))
                else:
                    raise TypeError(f"Unknown event type: {type(e)}")

        # django-components 0.134 기준 (2025-03)
        return cls.render(
            kwargs={"events": _events},
            slots={"default": message},
            escape_slots_content=True,
            type="document",  # RenderType
            render_dependencies=True,
            request=request,
        )

    @classmethod
    def make_response(
        cls,
        request: HttpRequest,
        message: str,
        event_name: Optional[str] = None,
        event_params: Optional[dict[str, Any]] = None,
        event: Optional[AlertEvent] = None,
        events: Optional[list[Union[AlertEvent, str]]] = None,
    ) -> HttpResponse:

        content = cls.make_html(
            request=request,
            message=message,
            event_name=event_name,
            event_params=event_params,
            event=event,
            events=events,
        )
        return cls.response_class(content)


class AlertInfo(Alert):
    context_data = {"type": "info"}


class AlertSuccess(Alert):
    context_data = {"type": "success"}


class AlertWarning(Alert):
    context_data = {"type": "warning"}


class AlertError(Alert):
    context_data = {"type": "error"}


# @registery 장식자를 적용하면 클래스가 Alert 타입이 아닌 Component 타입이 되므로
# 각 컴포넌트에 추가한 메서드들을 외부에서 인지하지 못하기에 장식자없이 수동으로 등록
registry.register("alert", Alert)
registry.register("alert_info", AlertInfo)
registry.register("alert_success", AlertSuccess)
registry.register("alert_warning", AlertWarning)
registry.register("alert_error", AlertError)
