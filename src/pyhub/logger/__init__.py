import logging
from typing import Callable, Optional


class LogCapture:
    def __init__(
        self,
        logger_name: str = "pyhub",
        level: int = logging.INFO,
        log_message_handler: Optional[Callable[[logging.LogRecord], None]] = None,
    ) -> None:
        self.logger = logging.getLogger(logger_name)
        self.handler = None
        self.log_message_handler = log_message_handler
        self.level = level

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
