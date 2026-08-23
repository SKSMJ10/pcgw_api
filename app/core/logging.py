import logging
import logging.config


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[31;1m",  # Bold Red
    }
    GRAY = "\033[90m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self._formatters = {}
        for level, color in self.COLORS.items():
            colored_fmt = f"{color}%(levelname_colon)-9s{self.RESET} {self.BLUE}%(asctime)s{self.RESET} - {self.MAGENTA}%(name)s{self.RESET} - %(message)s"
            self._formatters[level] = logging.Formatter(
                fmt=colored_fmt, datefmt=datefmt
            )

        self._fallback = logging.Formatter(
            fmt=f"%(levelname_colon)-7s {self.BLUE}%(asctime)s{self.RESET} - {self.MAGENTA}%(name)s{self.RESET} - %(message)s",
            datefmt=datefmt,
        )

    def format(self, record):
        record.levelname_colon = f"{record.levelname}:"
        formatter = self._formatters.get(record.levelname, self._fallback)
        return formatter.format(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "custom": {
            "()": ColorFormatter,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "console": {
            "formatter": "custom",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        "httpx": {"level": "WARNING"},
        "app": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
