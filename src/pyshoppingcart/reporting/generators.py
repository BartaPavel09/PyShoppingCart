"""Custom iterators and generator functions for PyShoppingCart."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Sequence

from pyshoppingcart.models.order import Order
from pyshoppingcart.models.product import Product


def low_stock_scanner(
    products: Iterable[Product],
    threshold: int = 5,
) -> Iterator[Product]:
    """Generator yielding products whose available stock is at or below threshold.

    Demonstrates lazy evaluation and memory efficiency (Lab 2 iter_03.py):
    Only inspects and yields items as requested by consumer, rather than building
    an entire list in memory.
    """
    for product in products:
        if product.stock <= threshold:
            yield product


class OrderBatchIterator:
    """Custom iterator class streaming orders in fixed-size chunks/batches.

    Implements Python's formal Iterator protocol (__iter__ and __next__ raising StopIteration).
    """

    def __init__(self, orders: Sequence[Order], batch_size: int = 5) -> None:
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        self._orders: Sequence[Order] = orders
        self._batch_size: int = batch_size
        self._cursor: int = 0

    def __iter__(self) -> OrderBatchIterator:
        return self

    def __next__(self) -> list[Order]:
        if self._cursor >= len(self._orders):
            raise StopIteration
        end = min(self._cursor + self._batch_size, len(self._orders))
        batch = list(self._orders[self._cursor:end])
        self._cursor = end
        return batch
