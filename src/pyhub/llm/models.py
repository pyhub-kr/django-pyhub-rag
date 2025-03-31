from django.db import models
from django.db.models import QuerySet

from pyhub.parser.upstage.types import ElementCategoryEnum


class ImageDescriptorPromptQuerySet(QuerySet):
    pass


class AbstractImageDescriptorPrompt(models.Model):
    category = models.CharField(
        max_length=20,
        choices=ElementCategoryEnum.choices,  # noqa
        default=ElementCategoryEnum.DEFAULT,
    )
    system_prompt = models.TextField()
    user_prompt = models.TextField(blank=True)

    objects = ImageDescriptorPromptQuerySet.as_manager()

    class Meta:
        abstract = True


class ImageDescriptorPrompt(AbstractImageDescriptorPrompt):
    class Meta:
        db_table = "pyhub_llm_image_descriptor_prompt"


__all__ = ["AbstractImageDescriptorPrompt", "ImageDescriptorPrompt"]
