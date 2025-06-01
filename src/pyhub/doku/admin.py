import json

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html

from .models import (
    Document,
    DocumentParseJob,
    ExtractedInformation,
    VectorDocument,
    VectorDocumentImage,
)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    pass


@admin.register(DocumentParseJob)
class DocumentParseJobAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "status")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CategoryListFilter(SimpleListFilter):
    title = "Category"
    parameter_name = "category"

    def lookups(self, request, model_admin):
        # 고유한 카테고리 값들을 가져옴
        categories = set()
        for doc in model_admin.model.objects.all():
            if doc.metadata and "category" in doc.metadata:
                categories.add(doc.metadata["category"])
        return [(cat, cat) for cat in sorted(categories)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(metadata__contains={"category": self.value()})
        return queryset


@admin.register(VectorDocument)
class VectorDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "category")
    list_filter = (CategoryListFilter,)

    def category(self, obj):
        return obj.metadata.get("category")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VectorDocumentImage)
class VectorDocumentImageAdmin(admin.ModelAdmin):
    # list_display = ("vector_document", "file", "name", "description")

    def vector_document_name(self, obj):
        pass

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExtractedInformation)
class ExtractedInformationAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "schema_name", "extraction_type", "created_at", "has_error")
    list_filter = ("extraction_type", "document_type", "schema_name", "created_at")
    search_fields = ("document__name", "schema_name")
    readonly_fields = ("document", "extracted_data_pretty", "error_message", "created_at", "updated_at")

    def has_error(self, obj):
        return bool(obj.error_message)

    has_error.boolean = True
    has_error.short_description = "Error"

    def extracted_data_pretty(self, obj):
        """Display extracted data in a pretty format"""
        if obj.extracted_data:
            return format_html(
                '<pre style="white-space: pre-wrap;">{}</pre>',
                json.dumps(obj.extracted_data, indent=2, ensure_ascii=False),
            )
        return "-"

    extracted_data_pretty.short_description = "Extracted Data"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
