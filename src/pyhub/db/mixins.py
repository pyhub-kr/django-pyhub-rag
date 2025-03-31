from django.db import models
from django.db.models import QuerySet
from django.utils.safestring import SafeString, mark_safe


class StatusQuerySet(QuerySet):
    def pending(self):
        return self.filter(status=self.model.Status.PENDING)

    def processing(self):
        return self.filter(status=self.model.Status.PROCESSING)

    def completed(self):
        return self.filter(status=self.model.Status.COMPLETED)

    def failed(self):
        return self.filter(status=self.model.Status.FAILED)


class StatusMixin(models.Model):
    """문서 처리 상태를 관리하는 추상 클래스"""

    class Status(models.IntegerChoices):
        PENDING = 0, "대기 중"
        PROCESSING = 1, "변환 중"
        COMPLETED = 2, "완료"
        FAILED = 3, "변환 실패"

    status = models.PositiveSmallIntegerField(
        choices=Status.choices,  # noqa
        default=Status.PENDING,
        editable=False,
    )

    objects = StatusQuerySet.as_manager()

    def status_label(self) -> SafeString:
        status = self.Status(self.status)
        label = self.get_status_display()
        match status:
            case self.Status.PENDING:
                label = f"<span class='inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800'>⏳ {label}</span>"
            case self.Status.PROCESSING:
                label = f"""
<span class='inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800'>
    <svg class='w-4 h-4 animate-spin mr-1' xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24'>
        <circle class='opacity-25' cx='12' cy='12' r='10' stroke='currentColor' stroke-width='4'></circle>
        <path class='opacity-75' fill='currentColor'
              d='M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z'>
        </path>
    </svg>
    {label}
</span>
"""
            case self.Status.COMPLETED:
                label = f"<span class='inline-flex items-center rounded-md bg-green-100 px-2 py-1 text-xs font-medium text-green-800'>✅ {label}</span>"
            case self.Status.FAILED:
                label = f"<span class='inline-flex items-center rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-800'>❌ {label}</span>"
            case _:
                label = "<span class='inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800'>Unknown</span>"
        return mark_safe(label)

    def needs_refresh(self) -> bool:
        return self.status not in (self.Status.COMPLETED, self.Status.FAILED)

    def pending(self):
        self.status = self.Status.PENDING
        self.save(update_fields=["status"])

    def processing(self):
        self.status = self.Status.PROCESSING
        self.save(update_fields=["status"])

    def completed(self):
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status"])

    def failed(self, e: Exception):
        self.status = self.Status.FAILED
        self.save(update_fields=["status"])

    class Meta:
        abstract = True


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


__all__ = ["StatusMixin", "TimestampedMixin"]
