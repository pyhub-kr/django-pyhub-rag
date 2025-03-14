from django.db import models


class JobStatus(models.TextChoices):
    PENDING = "pe", "Pending"
    PROCESSING = "pr", "Processing"
    COMPLETED = "co", "Completed"
    FAILED = "fa", "Failed"


class Language(models.TextChoices):
    KOREAN = "ko", "Korean"
    ENGLISH = "en", "English"
    JAPANESE = "ja", "Japanese"
    CHINESE = "zh", "Chinese"
