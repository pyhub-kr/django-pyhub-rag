from django.urls import path

from .views import (
    DocumentDeleteView,
    DocumentFormView,
    DocumentListView,
    DocumentParseJobListView,
    VectorDocumentDeleteView,
    VectorDocumentImageDeleteView,
    VectorDocumentImageListView,
    VectorDocumentImageUpdateView,
    VectorDocumentListView,
    VectorDocumentUpdateView,
    document_export,
    document_query,
)

app_name = "doku"

urlpatterns = (
    [
        path("", DocumentListView.as_view(), name="document-list"),
        path("new/", DocumentFormView.as_view(), name="document-new"),
        path("<int:pk>/delete/", DocumentDeleteView.as_view(), name="document-delete"),
        path("<int:pk>/", document_export, name="document-export"),
        path("<int:pk>/edit/", DocumentFormView.as_view(), name="document-edit"),
        path("<int:pk>/query/", document_query, name="document-query"),
    ]
    + [
        path(
            "<int:document_pk>/document-parse-jobs/",
            DocumentParseJobListView.as_view(),
            name="documentparsejobs-list",
        ),
    ]
    + [
        path(
            "<int:document_pk>/vector-documents/",
            VectorDocumentListView.as_view(),
            name="vectordocument-list",
        ),
        path(
            "<int:document_pk>/vector-documents/<int:pk>/edit/",
            VectorDocumentUpdateView.as_view(),
            name="vectordocument-edit",
        ),
        path(
            "<int:document_pk>/vector-documents/<int:pk>/delete/",
            VectorDocumentDeleteView.as_view(),
            name="vectordocument-delete",
        ),
    ]
    + [
        path(
            "<int:document_pk>/vector-documents/<int:vectordocument_pk>/images/",
            VectorDocumentImageListView.as_view(),
            name="vectordocumentimage-list",
        ),
        path(
            "vectordocumentimages/<int:pk>/edit/",
            VectorDocumentImageUpdateView.as_view(),
            name="vectordocumentimage-edit",
        ),
        path(
            "vectordocumentimages/<int:pk>/delete/",
            VectorDocumentImageDeleteView.as_view(),
            name="vectordocumentimage-delete",
        ),
    ]
)
