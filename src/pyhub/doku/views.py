from typing import Optional

from django.db.models import Count
from django.forms import ModelForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.generic import DeleteView, ListView

from pyhub.ui.modal.modal import Modal
from pyhub.ui.views import ModalFormView

from .forms import (
    DocumentForm,
    DocumentQueryForm,
    VectorDocumentForm,
    VectorDocumentImageDescriptionForm,
)
from .models import Document, DocumentParseJob, VectorDocument, VectorDocumentImage

#
# Document
#


class DocumentListView(ListView):
    model = Document
    queryset = Document.objects.prefetch_related("parse_job_set").order_by("-pk")
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()

        pk = self.request.GET.get("pk", None)
        if pk:
            qs = qs.filter(pk=pk)

        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["doku/document_list.html#list"]
        return ["doku/document_list.html"]


class DocumentFormView(ModalFormView):
    model = Document
    form_class = DocumentForm

    def form_valid(self, form: ModelForm) -> HttpResponse:
        res = super().form_valid(form)
        res["HX-Refresh"] = "true"
        return res


class DocumentDeleteView(DeleteView):
    model = Document

    def form_valid(self, form):
        # 페이지 이동 응답하지 않고, 삭제 후에 ok 응답 (이 응답이 로직에 사용되진 않습니다.)
        self.object.delete()
        return HttpResponse("ok")


def document_export(request: HttpRequest, pk: int) -> HttpResponse:
    document = get_object_or_404(Document, pk=pk)

    fmt = request.GET.get("format", None)
    if fmt == "jsonl":
        response = HttpResponse(document.to_jsonl(), content_type="application/x-jsonlines")
        response["Content-Disposition"] = f'attachment; filename="#{document.name}.jsonl"'
        return response

    body = render_to_string(
        "doku/_document_export.html",
        {
            "document": document,
        },
        request=request,
    )
    return Modal.render_to_response(
        kwargs={
            "title": f"{document} - 내보내기",
        },
        slots={
            "body": body,
        },
        request=request,
    )


def document_query(request, pk):
    document = get_object_or_404(Document, pk=pk)
    doc_list = None

    if request.method == "GET":
        form = DocumentQueryForm(request=request)
        form.helper.attrs["hx-target"] = "closest .modal-body"
        body = render_to_string(
            "doku/_document_query.html",
            {
                "form": form,
                "doc_list": doc_list,
            },
            request=request,
        )
        return Modal.render_to_response(
            kwargs={"title": f"{document} - 유사 문서 조회"},
            slots={"body": body},
            request=request,
        )
    else:
        form = DocumentQueryForm(data=request.POST, request=request)
        form.helper.attrs["hx-target"] = "closest .modal-body"
        if form.is_valid():
            query: str = form.cleaned_data["query"]

            qs = document.vector_document_set.all()
            doc_list = qs.similarity_search(query)  # noqa

        return render(
            request,
            "doku/_document_query.html",
            {
                "form": form,
                "doc_list": doc_list,
            },
        )


#
# DocumentParseJob
#


class DocumentParseJobListView(ListView):
    model = DocumentParseJob
    queryset = DocumentParseJob.objects.all().order_by("-pk")
    template_name = "doku/_documentparsejob_list.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document: Optional[Document] = None

    def get(self, request, *args, **kwargs):
        self.document = get_object_or_404(Document, pk=self.kwargs["document_pk"])
        return super().get(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        body = render_to_string(self.get_template_names(), context, request=self.request)
        return Modal.render_to_response(
            kwargs={
                "title": "작업 히스토리",
            },
            slots={
                "body": body,
            },
            request=self.request,
        )


#
# Vector Document
#


class VectorDocumentListView(ListView):
    model = VectorDocument
    paginate_by = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document: Optional[Document] = None

    def get(self, request, *args, **kwargs):
        self.document = get_object_or_404(Document, pk=self.kwargs["document_pk"])
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()

        pk = self.request.GET.get("pk", None)
        if pk:
            qs = qs.filter(pk=pk)

        qs = qs.filter(document=self.document)
        qs = qs.prefetch_related("image_set")
        qs = qs.annotate(image_count=Count("image"))
        return qs.order_by("pk")

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["document"] = self.document
        return context_data

    def get_template_names(self):
        if self.request.htmx:
            return ["doku/vectordocument_list.html#list"]
        return ["doku/vectordocument_list.html"]


class VectorDocumentUpdateView(ModalFormView):
    model = VectorDocument
    form_class = VectorDocumentForm


class VectorDocumentDeleteView(DeleteView):
    model = VectorDocument


#
# Vector Document Image
#


class VectorDocumentImageListView(ListView):
    model = VectorDocumentImage
    paginate_by = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document: Optional[Document] = None
        self.vector_document: Optional[VectorDocument] = None

    def get(self, request, *args, **kwargs):
        self.vector_document = get_object_or_404(VectorDocument, pk=self.kwargs["vectordocument_pk"])
        self.document = self.vector_document.document
        if self.document.pk != self.kwargs["document_pk"]:
            raise Http404("The requested document pk does not match the retrieved document.")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()

        pk = self.request.GET.get("pk", None)
        if pk:
            qs = qs.filter(pk=pk)

        qs = qs.filter(vector_document=self.vector_document)
        return qs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["document"] = self.document
        context_data["vector_document"] = self.vector_document
        return context_data

    def get_template_names(self):
        if self.request.htmx:
            return ["doku/vectordocumentimage_list.html#list"]
        return ["doku/vectordocumentimage_list.html#list"]


class VectorDocumentImageUpdateView(ModalFormView):
    model = VectorDocumentImage
    form_class = VectorDocumentImageDescriptionForm
    success_event_name = "refresh-vectordocumentimage"


class VectorDocumentImageDeleteView(DeleteView):
    model = VectorDocumentImage

    def form_valid(self, form):
        # 페이지 이동 응답하지 않고, 삭제 후에 ok 응답 (이 응답이 로직에 사용되진 않습니다.)
        self.object.delete()
        return HttpResponse("ok")
