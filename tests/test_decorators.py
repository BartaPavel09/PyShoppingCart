"""Unit tests for timing and logging decorators."""

from __future__ import annotations

import time

from pyshoppingcart.utils.decorators import log_state_transition, timed_operation


def test_timed_operation_decorator() -> None:
    @timed_operation
    def slow_add(a: int, b: int) -> int:
        """Add two numbers after short sleep."""
        time.sleep(0.005)
        return a + b

    # Verify functools.wraps preserves metadata
    assert slow_add.__name__ == "slow_add"
    assert "Add two numbers" in (slow_add.__doc__ or "")

    result = slow_add(10, 25)
    assert result == 35


def test_log_state_transition_decorator() -> None:
    @log_state_transition("Audit")
    def do_work(x: int) -> int:
        return x * 2

    assert do_work.__name__ == "do_work"
    assert do_work(21) == 42
