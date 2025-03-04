import json
from json import JSONDecodeError
from json import JSONEncoder as OrigJSONEncoder

from pyhub.llm.types import Embed, EmbedList


class PyhubJSONEncoder(OrigJSONEncoder):
    def default(self, o):
        if isinstance(o, Embed):
            return o.array
        if isinstance(o, EmbedList):
            return [embed.array for embed in o.arrays]
        return super().default(o)


def json_loads(s, **kwargs):
    return json.loads(s, **kwargs)


def json_dumps(obj, **kwargs):
    return json.dumps(obj, cls=PyhubJSONEncoder, ensure_ascii=False, **kwargs)


__all__ = ["JSONDecodeError", "json_loads", "json_dumps"]
