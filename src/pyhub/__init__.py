from importlib.metadata import PackageNotFoundError, version

from .init import init


def get_version() -> str:
    try:
        return version("django-pyhub-rag")
    except PackageNotFoundError:
        return "not found"


__all__ = ["init", "get_version"]
