from django.conf import settings

DEFAULTS = {
    "RAG_OPENAI_API_KEY": None,
    "RAG_OPENAI_BASE_URL": "https://api.openai.com/v1",
    "RAG_EMBEDDING_MODEL": "text-embedding-3-small",
    "RAG_EMBEDDING_DIMENSIONS": 1536,
    "RAG_EMBEDDING_MAX_TOKENS_LIMIT": 8191,
}


class RagSettings:
    def __init__(self, defaults):
        self.defaults = defaults

    def __getattr__(self, attr):
        value = getattr(settings, attr, None)
        if value is None:
            try:
                value = self.defaults[attr]
            except KeyError:
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")

        return value


rag_settings = RagSettings(DEFAULTS)
