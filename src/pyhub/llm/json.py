from json import JSONDecodeError, loads, dumps
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse

from .types import Embed, EmbedList


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if hasattr(o, "to_dict"):
            return o.to_dict()

        if isinstance(o, Embed):
            return o.array
        if isinstance(o, EmbedList):
            return [embed.array for embed in o.arrays]

        return super().default(o)


def json_loads(s, **kwargs) -> Any:
    return loads(s, **kwargs)


def json_dumps(obj, **kwargs) -> str:
    kwargs.setdefault("ensure_ascii", False)
    return dumps(obj, cls=JSONEncoder, **kwargs)


class JSONResponse(HttpResponse):
    def __init__(
        self,
        data,
        encoder=JSONEncoder,
        safe=True,
        json_dumps_params=None,
        **kwargs,
    ):
        if safe and not isinstance(data, dict):
            raise TypeError(
                "In order to allow non-dict objects to be serialized set the "
                "safe parameter to False."
            )
        if json_dumps_params is None:
            json_dumps_params = {}
        kwargs.setdefault("content_type", "application/json")
        data = json_dumps(data, cls=encoder, **json_dumps_params)
        super().__init__(content=data, **kwargs)



__all__ = ["JSONDecodeError", "JSONEncoder", "JSONResponse", "json_loads", "json_dumps"]