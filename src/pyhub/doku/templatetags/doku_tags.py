import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def doku_minimum_style(text: str) -> str:
    # Replace 3 or more newlines with 2 newlines

    text = re.sub(r"^\s*# (.+)$", r'<h1 class="text-2xl font-bold mt-2 mb-2"># \1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r"^\s*## (.+)$", r'<h2 class="text-xl font-semibold mt-1 mb-1">## \1</h2>', text, flags=re.MULTILINE)
    text = re.sub(
        r"^\s*### (.+)$", r'<h3 class="text-lg font-semibold mt-1 mb-1">### \1</h3>', text, flags=re.MULTILINE
    )
    text = re.sub(
        r"^\s*#### (.+)$", r'<h4 class="text-base font-semibold mt-1 mb-1">#### \1</h4>', text, flags=re.MULTILINE
    )
    text = re.sub(
        r"^\s*##### (.+)$", r'<h5 class="text-sm font-semibold mt-1 mb-1">##### \1</h5>', text, flags=re.MULTILINE
    )
    text = re.sub(
        r"^\s*###### (.+)$", r'<h6 class="text-xs font-semibold mt-1 mb-1">###### \1</h6>', text, flags=re.MULTILINE
    )
    return mark_safe(text)
