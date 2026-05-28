import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog.

    Local dev gets a pretty, colored console renderer (easy to read in a
    terminal). Everywhere else: JSON, one record per line, ready for log
    aggregators.
    """

    is_local = settings.environment == "local"
    level = logging.DEBUG if is_local else logging.INFO

    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # ConsoleRenderer wants a string traceback (via format_exc_info); the
    # JSON renderer wants the structured dict_tracebacks form. Pair them
    # correctly so the dev terminal doesn't blow up on unhandled exceptions.
    if is_local:
        traceback_processor: structlog.types.Processor = structlog.processors.format_exc_info
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True, sort_keys=False
        )
    else:
        traceback_processor = structlog.processors.dict_tracebacks
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            traceback_processor,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
