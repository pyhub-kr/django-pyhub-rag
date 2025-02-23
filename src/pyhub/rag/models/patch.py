"""
이 모듈은 Django 모델의 Options 클래스를 패치하여 Meta에 지정한
`db_alias` 옵션(문자열 또는 딕셔너리 타입)을 _meta에 저장하도록 합니다.
"""

from django.db.models import options

# allowed meta 옵션 목록에 'db_alias'를 추가합니다.
# Django의 기본 DEFAULT_NAMES에 'db_alias'가 포함되지 않으므로 이를 확장합니다.
if "db_alias" not in options.DEFAULT_NAMES:
    options.DEFAULT_NAMES = options.DEFAULT_NAMES + ("db_alias",)


# 원래 Options.__init__ 함수를 보관합니다.
_original_options_init = options.Options.__init__


def _new_options_init(self, meta, app_label):
    # 원래의 초기화 메서드를 호출하여 기본 동작을 수행합니다.
    _original_options_init(self, meta, app_label)
    # Meta에 db_alias가 정의되어있으면 _meta에 할당합니다.
    self.db_alias = getattr(meta, "db_alias", None)


# Django의 Options __init__를 새 함수로 대체합니다.
options.Options.__init__ = _new_options_init
