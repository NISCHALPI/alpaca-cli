"""Decorators for CLI commands."""

import functools
from typing import Callable, TypeVar, Any
from alpaca_cli.logger.logger import get_logger

F = TypeVar("F", bound=Callable[..., Any])

logger = get_logger("cli")


def handle_api_errors(func: F) -> F:
    """
    Decorator that wraps CLI commands with consistent error handling.

    Catches exceptions and logs them using the logger instead of
    letting them propagate with raw stack traces.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return None
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return None

    return wrapper  # type: ignore


def require_market_open(allow_extended: bool = False) -> Callable[[F], F]:
    """
    Decorator that ensures market is open before executing command.

    Args:
        allow_extended: If True, allow execution during extended hours.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from alpaca_cli.core.client import get_trading_client

            # Check if force flag is passed
            force = kwargs.get("force", False)
            if force:
                return func(*args, **kwargs)

            try:
                client = get_trading_client()
                clock = client.get_clock()

                if not clock.is_open:
                    logger.error(
                        "Market is closed. Use --force to override or wait for market open."
                    )
                    return None

                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Failed to check market status: {e}")
                return None

        return wrapper  # type: ignore

    return decorator
