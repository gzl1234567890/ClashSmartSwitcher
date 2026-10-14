import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re


class RedactingFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.secrets = set()

    def filter(self, record):
        message = record.getMessage()
        for secret in self.secrets:
            if secret:
                message = message.replace(secret, "[密钥已隐藏]")
        message = re.sub(r"(?i)(Bearer\s+)[^\s]+", r"\1[隐藏]", message)
        record.msg, record.args = message, ()
        return True


def setup_logging(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("smart-switcher")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(directory / "application.log", maxBytes=2 * 1024 * 1024, backupCount=4, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    redactor = RedactingFilter()
    handler.addFilter(redactor)
    logger.addHandler(handler)
    return logger, redactor
