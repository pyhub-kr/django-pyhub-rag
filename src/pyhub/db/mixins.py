from django.db import models


class StatusMixin(models.Model):
    """문서 처리 상태를 관리하는 추상 클래스"""

    class Status(models.IntegerChoices):
        PENDING = 0, "Pending"
        PROCESSING = 1, "Processing"
        COMPLETED = 2, "Completed"
        FAILED = 3, "Failed"

    status = models.PositiveSmallIntegerField(
        choices=Status.choices,  # noqa
        default=Status.PENDING,
        editable=False,
    )

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


__all__ = ["StatusMixin"]