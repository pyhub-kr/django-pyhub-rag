import tiktoken
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import ngettext_lazy


@deconstructible
class MaxTokenValidator(BaseValidator):
    message = ngettext_lazy(
        "The number of tokens must be at most %(limit_value)d (currently %(show_value)d).",
        "The number of tokens must be at most %(limit_value)d (currently %(show_value)d).",
        "limit_value",
    )
    code = "max_tokens"

    # https://platform.openai.com/docs/guides/embeddings
    max_input_tokens = {
        "text-embedding-3-small": 8191,
        "text-embedding-3-large": 8191,
        "text-embedding-ada-002": 8191,
    }

    def __init__(
        self,
        model_name="text-embedding-3-small",
        message=None,
    ):
        # limit_value 인자로 함수를 전달하면 유효성 검사를 수행하는 시점에 함수가 호출되어
        # 반환된 값을 limit_value 값으로 사용합니다.
        def get_limit_value():
            try:
                return self.max_input_tokens[model_name]
            except KeyError:
                raise ValidationError("Not found max input tokens for '%s'" % model_name)

        self.model_name = model_name
        super().__init__(limit_value=get_limit_value, message=message)

    def compare(self, a, b) -> bool:
        return a > b

    def clean(self, x: str) -> int:
        try:
            encoding: tiktoken.Encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            raise ValidationError("Not found encoding for '%s'" % self.model_name)
        num_tokens = len(encoding.encode(x or ""))
        return num_tokens
