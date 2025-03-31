import logging
from typing import cast

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from pyhub.parser.upstage.parser import ImageDescriptor

from .models import ImageDescriptorPrompt
from .types import LanguageEnum, LLMChatModelEnum, LLMVendorEnum, LLMVendorType

logger = logging.getLogger(__name__)


class ImageDescriptorMixin(models.Model):
    image_descriptor_llm_vendor = models.CharField(
        max_length=10,
        choices=LLMVendorEnum.choices,  # noqa
        default=LLMVendorEnum.OPENAI,
    )
    image_descriptor_llm_model = models.CharField(
        max_length=50,
        choices=LLMChatModelEnum.choices,
        default=LLMChatModelEnum.GPT_4O_MINI,
        help_text="지정 API의 API Key 설정이 없다면 동작하지 않습니다.",
    )
    image_descriptor_temperature = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=0.25,
    )
    image_descriptor_max_tokens = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(8192)],
        default=2000,
    )
    image_descriptor_language = models.CharField(
        max_length=50,
        choices=LanguageEnum.choices,
        default=LanguageEnum.KOREAN,
        help_text="이미지 설명 생성에 사용할 대상 언어",
    )

    def clean(self):
        """vendor 별 model 유효성 검사"""

        super().clean()

        LLMChatModelEnum.validate_model(
            llm_vendor=cast(LLMVendorType, self.image_descriptor_llm_vendor),
            chat_model=self.image_descriptor_llm_model,
        )

    def get_image_descriptor(self) -> ImageDescriptor:
        qs = ImageDescriptorPrompt.objects.all()
        qs = qs.values_list("category", "system_prompt", "user_prompt")

        system_prompts = {}
        user_prompts = {}
        for category, system_prompt, user_prompt in qs:
            if system_prompt:
                system_prompts[category] = system_prompt
            if user_prompt:
                user_prompts[category] = user_prompt

        logger.debug("loaded %d system prompts", len(system_prompts))
        logger.debug("loaded %d user prompts", len(user_prompts))

        # TODO: 프롬프트에 language 등의 필수 인자 지정이 있는 지 검사하기

        return ImageDescriptor(
            llm_vendor=cast(LLMVendorType, self.image_descriptor_llm_vendor),
            llm_model=self.image_descriptor_llm_model,
            temperature=self.image_descriptor_temperature,
            max_tokens=self.image_descriptor_max_tokens,
            prompt_context=dict(
                language=self.image_descriptor_language,
            ),
            system_prompts=system_prompts,
            user_prompts=user_prompts,
        )

    class Meta:
        abstract = True


__all__ = ["ImageDescriptorMixin"]
