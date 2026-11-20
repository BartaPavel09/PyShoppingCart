"""Execution timing and logging decorators for PyShoppingCart using functools.wraps and standard logging."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

# Set up module logger
logger = logging.getLogger("pyshoppingcart")

F = TypeVar("F", bound=Callable[..., Any])


def timed_operation(func: F) -> F:
    """Decorator that measures execution time of a function/method in milliseconds.

    Logs execution duration at DEBUG level and records performance metrics.
    Preserves wrapped function metadata via functools.wraps.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        func_name = getattr(func, "__qualname__", func.__name__)
        logger.debug(f"Starting operation: {func_name}")
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.debug(f"Completed {func_name} in {duration_ms:.2f} ms")
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"Operation {func_name} failed after {duration_ms:.2f} ms with: {exc}")
            raise

    return wrapper  # type: ignore[return-value]


def log_state_transition(operation_label: str) -> Callable[[F], F]:
    """Decorator factory recording business domain operations and state transitions.

    Args:
        operation_label: Short descriptor of the domain operation (e.g. 'Checkout', 'Restock').
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = getattr(func, "__qualname__", func.__name__)
            logger.info(f"[{operation_label}] Initiating {func_name}...")
            try:
                result = func(*args, **kwargs)
                logger.info(f"[{operation_label}] Successfully completed {func_name}")
                return result
            except Exception as exc:
                logger.error(f"[{operation_label}] Failed {func_name}: {exc}")
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
