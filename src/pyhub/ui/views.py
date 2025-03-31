from typing import Literal, Optional, Type

from crispy_forms.utils import render_crispy_form
from django.db.models import Model, QuerySet
from django.forms import ModelForm
from django.http import Http404, HttpRequest, HttpResponse
from django.template.context_processors import csrf
from django.utils.safestring import mark_safe
from django.views import View

from .alert.alert import AlertEvent, AlertWarning
from .modal.modal import Modal
from .toast_container.toast_container import ToastMessage


class ModalFormView(View):
    model: Type[Model]
    queryset: Optional[QuerySet] = None
    form_class: Type[ModelForm]
    create_title_format: str = "Create New"
    update_title_format: str = "Edit #{pk}"
    close_modal_event_delay: Optional[int] = 1  # ms
    success_alert_message = "Saved !"
    success_events: list[AlertEvent] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance: Optional[Model] = None
        self.mode: Literal["create", "update"] = "create"

    def get_object(self, pk: Optional[int] = None) -> Optional[Model]:
        if pk is None:
            self.mode = "create"
            return None

        self.mode = "update"

        if self.queryset is None:
            self.queryset = self.model._default_manager.all()

        try:
            return self.queryset.get(pk=pk)
        except self.queryset.model.DoesNotExist:
            raise Http404

    def get_title(self) -> str:
        if self.instance is None:
            params = SafeDict()
            return self.create_title_format.format_map(params)

        # KeyError를 발생시키지 않고, Key를 그대로 노출시킵니다.
        params = SafeDict(pk=self.instance.pk, **self.instance.__dict__)
        return self.update_title_format.format_map(params)

    def get(self, request: HttpRequest, pk: Optional[int] = None, **kwargs) -> HttpResponse:
        self.instance = self.get_object(pk)
        form = self.form_class(instance=self.instance)
        return self.render_response(form)

    def render_response(self, form: ModelForm) -> HttpResponse:
        if hasattr(form, "helper"):
            # ModalLinkButton 컴포넌트에서 지정하여 hx-vals를 통해 전달해주는 인자
            modal_container_id = self.request.GET.get("modal_container_id", "modal-container")
            form.helper.attrs.update(
                {
                    "hx-post": self.request.get_full_path(),
                    "hx-target": f"#{modal_container_id}",
                    "hx-swap": "innerHTML",
                }
            )
            # https://django-crispy-forms.readthedocs.io/en/stable/crispy_tag_forms.html#ajax-validation-recipe
            form_html = render_crispy_form(form, context=csrf(self.request))
        else:
            form_html = AlertWarning.make_html(
                request=self.request,
                message=f"{form.__class__.__name__} 클래스에 helper 설정이 누락되었습니다.",
            )

        return Modal.render_to_response(
            kwargs={"title": self.get_title()},
            slots={"body": form_html},
            request=self.request,
        )

    def post(self, request: HttpRequest, pk: Optional[int] = None, **kwargs) -> HttpResponse:
        self.instance = self.get_object(pk)
        form = self.form_class(
            data=request.POST,
            files=request.FILES,
            instance=self.instance,
        )
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form: ModelForm) -> HttpResponse:
        self.instance = form.save()

        # 모두 as_html 메서드를 지원하는 객체로만 구성했습니다.
        events = [
            ToastMessage(
                type="success",
                message=self.success_alert_message,
            ),
            AlertEvent("close-modal", delay=self.close_modal_event_delay),
            *self.get_success_events(),
        ]

        html = mark_safe("\n".join(e.as_html() for e in events))

        return Modal.render_to_response(
            kwargs={"title": self.get_title()},
            slots={"body": html},
            request=self.request,
        )

    def form_invalid(self, form: ModelForm) -> HttpResponse:
        return self.render_response(form)

    def get_success_events(self) -> list[AlertEvent]:
        # VectorDocumentImage to "vectordocumentimage"
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        if self.mode == "create":
            alert_events = [
                AlertEvent(f"created-{app_label}-{model_name}", {"pk": self.instance.pk}),
            ]
        elif self.mode == "update":
            alert_events = [
                AlertEvent(f"updated-{app_label}-{model_name}", {"pk": self.instance.pk}),
                AlertEvent(f"updated-{app_label}-{model_name}-{self.instance.pk}", {"pk": self.instance.pk}),
            ]
        else:
            raise ValueError(f"Invalid mode = {self.mode}")

        return [*alert_events, *self.success_events]


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"
