import logging
from typing import Literal, Type, Union, cast

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model

logger = logging.getLogger(__name__)


class Router:
    def _get_db_alias(
        self,
        model_cls: Union[str, Model, Type[Model]],
        operation_type: Literal["read", "write", "migrate"],
    ) -> str:
        """모델에 대한 데이터베이스 별칭을 반환합니다.

        Args:
            model_cls: 모델 클래스, 모델 인스턴스 또는 'app_label.model_name' 형식의 문자열
            operation_type: 데이터베이스 작업 유형 ('read', 'write', 'migrate' 중 하나)

        Returns:
            str: 데이터베이스 별칭

        Raises:
            ValueError: db_alias가 잘못된 형식이거나 operation_type에 대한 설정이 없는 경우
        """

        if isinstance(model_cls, str):
            app_label, model_name = model_cls.split(".", 1)
            model_cls = cast(Type[Model], apps.get_model(app_label, model_name))
        elif isinstance(model_cls, Model):
            model_cls = model_cls.__class__

        db_alias = getattr(model_cls._meta, "db_alias", None)
        if db_alias is None:
            return "default"
        elif isinstance(db_alias, str):
            return db_alias
        elif isinstance(db_alias, dict):
            alias = db_alias.get(operation_type)
            if alias is None:
                raise ImproperlyConfigured(
                    f"{model_cls} 모델의 Meta 설정에 {operation_type}에 대한 db_alias가 설정되어 있지 않습니다."
                )
            return alias
        else:
            raise ValueError(f"지원하지 않는 db_alias 타입 : {type(db_alias)}")

    def allow_relation(self, model_obj1: Model, model_obj2: Model, **hints) -> bool:
        """두 모델 객체 간의 관계 설정 허용 여부를 결정합니다.

        Args:
            model_obj1: 첫 번째 모델 객체
            model_obj2: 두 번째 모델 객체
            **hints: 추가 힌트

        Returns:
            bool: 관계 설정 허용 여부
        """

        return True

    def db_for_read(self, model_cls: Type[Model], **hints) -> str:
        """읽기 작업에 사용할 데이터베이스 별칭을 반환합니다.

        Args:
            model_cls: 모델 클래스
            **hints: 추가 힌트

        Returns:
            str: 데이터베이스 별칭
        """

        db_alias = self._get_db_alias(model_cls, "read")
        logger.debug("db_for_read : %s -> %s", model_cls, db_alias)
        return db_alias

    def db_for_write(self, model_cls: Type[Model], **hints) -> str:
        """쓰기 작업에 사용할 데이터베이스 별칭을 반환합니다.

        Args:
            model_cls: 모델 클래스
            **hints: 추가 힌트

        Returns:
            str: 데이터베이스 별칭
        """

        db_alias = self._get_db_alias(model_cls, "write")
        logger.debug("db_for_write : %s -> %s", model_cls, db_alias)
        return db_alias

    def allow_migrate(self, target_db_alias, app_label, model_name=None, **hints) -> bool:
        """마이그레이션 수행 허용 여부를 결정합니다.

        `python manage.py migrate` 명령 실행 시 실제 데이터베이스 마이그레이션 수행 여부를 결정합니다.
        False를 반환하면 마이그레이션이 실행되지 않지만, django_migrations 테이블에는 수행된 것으로 기록됩니다.

        Args:
            target_db_alias: 대상 데이터베이스 별칭
            app_label: 앱 레이블
            model_name: 모델 이름 (선택사항)
            **hints: 추가 힌트

        Returns:
            bool: 마이그레이션 허용 여부
        """

        if model_name is None:
            db_alias = "default"
        else:
            model_cls = cast(Type[Model], apps.get_model(app_label, model_name))
            if model_cls._meta.managed is False:
                logger.debug(
                    "db_for_write : target_db_alias(%s), app_label(%s), model_name(%s) -> unmanaged model",
                    target_db_alias,
                    app_label,
                    model_name,
                )
                return False

            db_alias = self._get_db_alias(model_cls, "migrate")

        logger.debug(
            "db_for_write : target_db_alias(%s), app_label(%s), model_name(%s) -> %s",
            target_db_alias,
            app_label,
            model_name,
            db_alias,
        )

        return target_db_alias == db_alias
