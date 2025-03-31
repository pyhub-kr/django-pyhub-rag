from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from .models import Document, DocumentParseJob, VectorDocument, VectorDocumentImage


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
