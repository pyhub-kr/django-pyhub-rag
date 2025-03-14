import json
from typing import Any


class PyhubParserJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "to_dict"):
            return o.to_dict()
        return super().default(o)


def json_loads(s, **kwargs) -> Any:
    return json.loads(s, **kwargs)


def json_dumps(obj, **kwargs) -> str:
    return json.dumps(obj, cls=PyhubParserJSONEncoder, ensure_ascii=False, **kwargs)


__all__ = ["PyhubParserJSONEncoder", "json_loads", "json_dumps"]
