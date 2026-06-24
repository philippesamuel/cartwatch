import functools
import inspect

from loguru import logger
from prefect import get_run_logger


def forward_logs(func):
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            configure_logger()
            return await func(*args, **kwargs)
        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        configure_logger()
        return func(*args, **kwargs)
    return sync_wrapper


handler_ids: list[int] = []


def configure_logger():
    global handler_ids

    try:
        # Passthrough in case we are outside of a task / flow context, e.g. `.fn`
        run_logger = get_run_logger()
    except Exception:
        return

    for handler_id in handler_ids:
        try:
            logger.remove(handler_id)
        except ValueError:
            pass

    log_format = "{message}"

    handler_ids.append(
        logger.add(
            run_logger.debug,
            filter=lambda record: record["level"].name == "DEBUG",
            level="TRACE",
            format=log_format,
        )
    )

    handler_ids.append(
        logger.add(
            run_logger.warning,
            filter=lambda record: record["level"].name == "WARNING",
            level="TRACE",
            format=log_format,
        )
    )

    handler_ids.append(
        logger.add(
            run_logger.error,
            filter=lambda record: record["level"].name == "ERROR",
            level="TRACE",
            format=log_format,
        )
    )

    handler_ids.append(
        logger.add(
            run_logger.critical,
            filter=lambda record: record["level"].name == "CRITICAL",
            level="TRACE",
            format=log_format,
        )
    )

    handler_ids.append(
        logger.add(
            run_logger.info,
            filter=lambda record: record["level"].name
            not in ["DEBUG", "WARNING", "ERROR", "CRITICAL"],
            level="TRACE",
            format=log_format,
        )
    )


