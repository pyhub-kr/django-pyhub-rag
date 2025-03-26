from typing import Type, TypeVar, get_args

from django.db.models import TextChoices


def type_to_flatten_set(type_: TypeVar) -> set[str]:
    result = set()

    for arg in get_args(type_):
        if isinstance(arg, str):
            result.add(arg.lower())
        elif hasattr(arg, "__args__"):
            for val in arg.__args__:
                if isinstance(val, str):
                    result.add(val.lower())

    return result


def enum_to_flatten_set(enum: Type[TextChoices]) -> set[str]:
    return set(map(lambda s: s.lower(), enum.values))
