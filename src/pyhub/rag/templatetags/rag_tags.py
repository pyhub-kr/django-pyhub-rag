from uuid import uuid4

from django import template

register = template.Library()


@register.simple_tag
def uuid4_id(prefix="id_") -> str:
    return (prefix or "") + uuid4().hex
