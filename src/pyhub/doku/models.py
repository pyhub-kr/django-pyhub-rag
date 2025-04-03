import logging
from io import StringIO

from django.core.validators import MinValueValidator
from django.db import models
from django_lifecycle import AFTER_SAVE, BEFORE_SAVE, LifecycleModelMixin, hook

from pyhub.core.models.fields import PageNumbersField, PDFFileField
from pyhub.db.mixins import StatusMixin, TimestampedMixin
from pyhub.llm.json import json_dumps
from pyhub.llm.mixins import ImageDescriptorMixin
from pyhub.parser.upstage.types import DocumentSplitStrategyEnum
from pyhub.rag.models.postgres import PGVectorDocument

logger = logging.getLogger(__name__)


class Document(
    LifecycleModelMixin,
    ImageDescriptorMixin,
    StatusMixin,
    TimestampedMixin,
    models.Model,
):
    """사용자가 업로드한 문서 파일"""

    class Engine(models.TextChoices):
        UPSTAGE_DOCUMENT_PARSE = "upstage/document_parse", "Upstage Document Parse API"

    engine = models.CharField(
        choices=Engine.choices,
        default=Engine.UPSTAGE_DOCUMENT_PARSE,
        verbose_name="문서 파싱 엔진",
    )
    file = PDFFileField(upload_to="doku/document/%Y/%m/%d", verbose_name="PDF 파일")
    name = models.CharField(max_length=255, blank=True, help_text="비워두시면 파일명이 자동으로 입력됩니다.")
    # summary = models.TextField(blank=True, verbose_name="문서 요약")

    start_page = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name="시작 페이지 번호", help_text="PDF 변환에서만 활용"
    )
    max_page = models.PositiveIntegerField(default=0, verbose_name="처리할 최대 페이지 수", help_text="0 : 모든 페이지")
    pages = PageNumbersField(blank=True, verbose_name="변환할 페이지 번호 (비워두시면 모든 페이지를 변환합니다.)")

    split_strategy = models.CharField(
        max_length=10,
        choices=[(e.value, e.name) for e in DocumentSplitStrategyEnum],
        default=DocumentSplitStrategyEnum.PAGE.value,
        verbose_name="Elements to Document 분할 전략",
        help_text="NONE: 분할없이 한 Document에 넣기",
    )

    class Meta:
        ordering = ("-id",)
        db_table = "pyhub_doku_document"

    def __str__(self) -> str:
        return self.name

    @hook(BEFORE_SAVE, when="file", has_changed=True)
    def on_before_save(self):
        """원본 파일명 저장"""
        if not self.name:
            self.name = self.file.name

    @hook(AFTER_SAVE, when="file", has_changed=True)
    def on_after_save(self):
        self.make_parse_job()

    def make_parse_job(self):
        """DocumentParseJob 생성"""
        self.vector_document_set.all().delete()
        DocumentParseJob.objects.pending().filter(document=self).delete()
        # TODO: celery를 통한 수행
        self.pending()
        DocumentParseJob.objects.create(document=self)

    def to_jsonl(self) -> str:
        with StringIO() as jsonl_file:
            for vector_document in self.vector_document_set.all().order_by("pk"):
                obj = json_dumps(
                    {
                        "pk": vector_document.pk,
                        "page_content": vector_document.page_content,
                        "metadata": vector_document.metadata,
                    }
                )
                print(obj, file=jsonl_file)

            jsonl_file.seek(0)
            return jsonl_file.read()


class DocumentParseJob(
    LifecycleModelMixin,
    StatusMixin,
    TimestampedMixin,
    models.Model,
):
    """PDF 파일 파싱 작업을 추적"""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="parse_job_set",
        related_query_name="parse_job",
    )
    log_messages = models.JSONField(default=list)  # TODO: 로그 추가

    def pending(self):
        super().pending()
        self.document.pending()

    def processing(self):
        super().processing()
        self.document.processing()

    def completed(self):
        super().completed()
        self.document.completed()

    def failed(self, e: Exception):
        logger.error("Failed to parse document: %s", e)
        super().failed(e)
        self.document.failed(e)

    class Meta:
        ordering = ["-pk"]
        db_table = "pyhub_doku_document_parse_job"


class VectorDocument(TimestampedMixin, PGVectorDocument):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="vector_document_set",
        related_query_name="vector_document",
    )

    class Meta:
        ordering = ["-pk"]
        db_table = "pyhub_doku_vector_document"
        indexes = [
            PGVectorDocument.make_hnsw_index(
                "doku_vecdoc_idx",  # 데이터베이스 내에서 유일한 이름으로 지정하셔야 합니다.
                # "vector",        # field type
                # "cosine",        # distance metric
            ),
        ]

    def update_image_descriptions(self):
        separator = "\n\n"
        self.metadata["image_descriptions"] = separator.join(self.image_set.values_list("description", flat=True))
        self.save(update_fields=["metadata"])


class VectorDocumentImage(LifecycleModelMixin, TimestampedMixin, models.Model):
    vector_document = models.ForeignKey(
        VectorDocument,
        on_delete=models.CASCADE,
        related_name="image_set",
        related_query_name="image",
    )
    file = models.ImageField(upload_to="doku/vector-document-image/%Y/%m/%d")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["pk"]
        db_table = "pyhub_doku_vector_document_image"

    @hook(AFTER_SAVE, when="description", has_changed=True)
    def on_after_save(self):
        # 부모 VectorDocument metadata["image_descriptions"] 업데이트
        self.vector_document.update_image_descriptions()