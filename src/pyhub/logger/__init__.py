import logging
from typing import Callable, Optional

from rich.console import Console


class LogCapture:
    def __init__(
        self,
        logger_name: str = "pyhub",
        level: int = logging.INFO,
        console: Optional[Console] = None,
        log_message_handler: Optional[Callable[[logging.LogRecord], None]] = None,
    ) -> None:
        self.logger = logging.getLogger(logger_name)
        self.handler = None
        self.console = console
        self.log_message_handler = log_message_handler
        self.level = level

        if self.console is not None and self.log_message_handler is None:
            self.log_message_handler = self.default_log_message_handler

    def __enter__(self):
        # 커스텀 핸들러 생성
        class LogStreamHandler(logging.StreamHandler):
            def __init__(self, log_message_handler):
                super().__init__()
                self.log_message_handler = log_message_handler

            def emit(self, record: logging.LogRecord) -> None:
                if self.log_message_handler:
                    self.log_message_handler(record)

        self.handler = LogStreamHandler(self.log_message_handler)
        self.logger.setLevel(self.level)
        self.handler.setLevel(self.level)
        self.logger.addHandler(self.handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            self.logger.removeHandler(self.handler)

    def default_log_message_handler(self, record: logging.LogRecord) -> None:
        """로그 레벨에 따라 다른 색상으로 메시지만 출력"""
        message = record.getMessage()

        if record.levelno >= logging.ERROR:
            self.console.print(f"[red]{message}[/red]")
        elif record.levelno >= logging.WARNING:
            self.console.print(f"[yellow]{message}[/yellow]")
        elif record.levelno >= logging.INFO:
            self.console.print(f"[green]{message}[/green]")
        else:  # DEBUG 및 기타 레벨
            self.console.print(f"[blue]{message}[/blue]")
