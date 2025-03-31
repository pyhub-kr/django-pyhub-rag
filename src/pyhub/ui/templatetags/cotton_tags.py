# https://github.com/wrabit/django-cotton/blob/main/django_cotton/templatetags/cotton.py

from django_cotton.templatetags.cotton import register

# django-components의 slot 템플릿 태그와 이름 충돌이 있어, 태그명 앞에 c_ 추가

if "slot" in register.tags:
    register.tags["c_slot"] = register.tags.pop("slot")
