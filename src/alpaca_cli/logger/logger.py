"""Logger module for CLI."""

import logging
import time
from functools import wraps
from typing import Callable, Any, Generator
from contextlib import contextmanager
from rich.logging import RichHandler


# Define a logging format


def configure_logging(level: str = "INFO") -> None:
    """Configure the logging system.

    Args:
        level: The logging level to use (default: "INFO")
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                omit_repeated_times=False,
            )
        ],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with a specific name.

    Args:
        name: The name of the logger

    Returns:
        logging.Logger: The configured logger instance
    """
    return logging.getLogger(name)


@contextmanager
def log_execution_time(
    logger: logging.Logger, task_name: str
) -> Generator[None, None, None]:
    """Context manager to log the execution time of a block of code.

    Args:
        logger: The logger instance to use
        task_name: Description of the task being measured
    """
    start_time = time.perf_counter()
    logger.info(f"Started: {task_name}")
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        logger.info(f"Finished: {task_name} (took {duration:.4f}s)")
