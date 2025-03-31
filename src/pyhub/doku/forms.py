from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Field, Fieldset, Layout, Row
from django import forms
from django.http import HttpRequest

from pyhub.ui.forms import CrispyLayoutAwareModelForm
from pyhub.ui.layout import EvenRow, JustOneClickableSubmit

from .models import Document, VectorDocument, VectorDocumentImage


class DocumentForm(CrispyLayoutAwareModelForm):
    regenerate = forms.BooleanField(
        required=False, label="재생성", help_text="체크하면 기존 벡터 문서를 삭제하고 다시 생성합니다."
    )

    class Meta:
        model = Document
        fields = [
            "engine",
            "image_descriptor_language",
            "image_descriptor_llm_vendor",
            "image_descriptor_llm_model",
            "image_descriptor_temperature",
            "image_descriptor_max_tokens",
            "split_strategy",
            "name",
            "file",
            "start_page",
            "max_page",
            "pages",
            "regenerate",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 수정에서만 regenerate 필드를 추가. 생성에서는 제거.
        if self.instance.pk is None:
            del self.fields["regenerate"]
            extra_fields = []
        else:
            extra_fields = ["regenerate"]

        self.fields["image_descriptor_language"].label = "생성 언어"
        self.fields["image_descriptor_llm_vendor"].label = "LLM Vendor"
        self.fields["image_descriptor_llm_model"].label = "LLM Model"
        self.fields["image_descriptor_temperature"].label = "Temperature"
        self.fields["image_descriptor_max_tokens"].label = "Max tokens"

        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": True}
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            EvenRow(
                "engine",
                "split_strategy",
            ),
            EvenRow("name", "file"),
            EvenRow("start_page", "max_page", "pages"),
            Fieldset(
                "Image Descriptor",
                EvenRow(
                    "image_descriptor_language",
                    "image_descriptor_llm_vendor",
                    "image_descriptor_llm_model",  # TODO: widget margin 스타일 조정
                    "image_descriptor_temperature",
                    "image_descriptor_max_tokens",
                ),
            ),
            *extra_fields,
            ButtonHolder(
                JustOneClickableSubmit(),
            ),
        )

    def save(self, commit=True):
        is_update = self.instance.pk is not None
        is_regenerate = self.cleaned_data.get("regenerate", False)
        is_run_on_after_save = self.instance.has_changed("file")
        instance = super().save(commit)

        if is_update and is_regenerate and is_run_on_after_save is False:
            instance.make_parse_job()

        return instance


class DocumentQueryForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "검색어를 입력해주세요.",
            }
        ),
        label="",
    )

    def __init__(self, *args, request: HttpRequest, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.attrs = {
            "novalidate": True,
            "hx-post": request.get_full_path(),
        }
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Field("query", wrapper_class="flex-grow"),
                JustOneClickableSubmit(css_class="flex-none ml-2"),
                css_class="flex items-start justify-start",
            ),
        )


class VectorDocumentForm(CrispyLayoutAwareModelForm):
    class Meta:
        model = VectorDocument
        fields = ["page_content", "metadata"]

    helper = FormHelper()
    helper.attrs = {"novalidate": True}
    helper.form_method = "post"
    helper.layout = Layout(
        "page_content",
        "metadata",
        ButtonHolder(
            JustOneClickableSubmit(),
        ),
    )


class VectorDocumentImageDescriptionForm(CrispyLayoutAwareModelForm):
    class Meta:
        model = VectorDocumentImage
        fields = ["description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": True}
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "description",
            ButtonHolder(
                JustOneClickableSubmit(),
            ),
        )
