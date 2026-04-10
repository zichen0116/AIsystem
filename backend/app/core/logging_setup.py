"""Application logging setup."""

import logging


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(debug: bool = False) -> None:
    """Configure root/app loggers without clobbering uvicorn handlers."""
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(handler)

    root_logger.setLevel(logging.INFO)
    logging.getLogger("app").setLevel(logging.DEBUG if debug else logging.INFO)

