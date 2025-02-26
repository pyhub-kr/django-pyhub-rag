import sqlite3
import sys

from django.core.management.base import BaseCommand

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None


class Command(BaseCommand):
    help = "Checks if the current Python environment supports sqlite-vec library"

    def _error_exit(self, message: str) -> None:
        """출력 에러 메시지와 함께 프로그램 종료"""
        self.stdout.write(self.style.ERROR(message))
        sys.exit(1)

    def handle(self, *args, **options):
        is_windows = sys.platform == "win32"
        is_arm = "ARM" in sys.version
        is_python_3_10_or_later = sys.version_info[:2] >= (3, 10)

        if is_windows and is_arm:
            self._error_exit(
                "❌ ARM version of Python does not support sqlite-vec library. Please reinstall AMD64 version of Python."
            )

        if not is_python_3_10_or_later:
            self._error_exit("❌ Python 3.10 or later is required.")

        if sqlite_vec is None:
            self._error_exit("❌ Please install sqlite-vec library.")

        with sqlite3.connect(":memory:") as db:
            try:
                db.enable_load_extension(True)
                sqlite_vec.load(db)  # Loading sqlite-vec extension
                db.enable_load_extension(False)
            except AttributeError:
                self._error_exit(
                    "❌ This Python does not support sqlite3 extension. Please refer to the guide and reinstall Python."
                )
            else:
                self.stdout.write(self.style.SUCCESS("✅ This Python supports sqlite3 extension."))
