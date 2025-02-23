import logging

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from django.dispatch import receiver

from pyhub.rag.utils import load_sqlite_vec_extension

logger = logging.getLogger(__name__)


@receiver(connection_created)
def load_sqlite_extension(sender, connection: BaseDatabaseWrapper, **kwargs):
    """
    SQLite 연결이 생성될 때마다 확장을 로드해야만 합니다.
    """

    logger.debug(
        "Received connection_created signal : %s from %s",
        connection.vendor,
        sender,
    )

    if connection.vendor == "sqlite":
        load_sqlite_vec_extension(connection.connection)
