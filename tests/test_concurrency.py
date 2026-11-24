"""Concurrency and thread synchronization acceptance tests for PyShoppingCart.

Acceptance Scenario:
  When multiple concurrent worker threads attempt to checkout the last item in stock:
  - Exactly one checkout succeeds.
  - All other threads raise InsufficientStockError.
  - Product inventory remains non-negative (>= 0).
  - Invariant holds: final_stock == initial_stock - quantity * successful_checkouts.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple

import pytest

from pyshoppingcart.exceptions import InsufficientStockError
from pyshoppingcart.models import Customer, Product
from pyshoppingcart.store import Store


class RaceTrialResult(NamedTuple):
    successful_checkouts: int
    failed_checkouts: int
    final_stock: int
    exceptions: list[Exception]


def run_concurrent_checkout_trial(
    store: Store,
    product_id: str,
    num_threads: int = 10,
    use_lock: bool = True,
    simulate_race_delay: float = 0.0,
) -> RaceTrialResult:
    """Execute a single concurrent race on a shared store product."""
    customers = [
        Customer(f"RACER-{i}", f"Shopper {i}", f"shopper{i}@race.com")
        for i in range(num_threads)
    ]
    for c in customers:
        store.register_customer(c)
        store.add_to_cart(c.id, product_id, quantity=1)

    successful = 0
    failed = 0
    exceptions: list[Exception] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(num_threads)

    def worker(customer_id: str) -> None:
        barrier.wait()  # Align thread start so all workers race simultaneously
        nonlocal successful, failed
        try:
            store.checkout(
                customer_id=customer_id,
                use_lock=use_lock,
                simulate_race_delay=simulate_race_delay,
            )
            with results_lock:
                successful += 1
        except Exception as exc:
            with results_lock:
                failed += 1
                exceptions.append(exc)

    threads = [
        threading.Thread(target=worker, args=(c.id,))
        for c in customers
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_stock = store.get_product(product_id).stock
    return RaceTrialResult(successful, failed, final_stock, exceptions)


class TestThreadSafetyAndSynchronization:
    """Acceptance tests verifying thread safety under concurrent workloads."""

    def test_single_item_concurrent_checkout_acceptance(self) -> None:
        """Core acceptance test: 1 item in stock, 10 concurrent threads racing."""
        store = Store()
        p = Product("RARE-01", "Last GPU in Stock", price_cents=50000, stock=1)
        store.add_product(p)

        res = run_concurrent_checkout_trial(
            store=store,
            product_id=p.id,
            num_threads=10,
            use_lock=True,
            simulate_race_delay=0.001,
        )

        # Acceptance Criteria Assertions
        assert res.successful_checkouts == 1, (
            f"Expected exactly 1 checkout to succeed, got {res.successful_checkouts}"
        )
        assert res.failed_checkouts == 9, (
            f"Expected 9 rejections, got {res.failed_checkouts}"
        )
        assert res.final_stock == 0, (
            f"Expected final stock 0, got {res.final_stock}"
        )
        assert all(isinstance(exc, InsufficientStockError) for exc in res.exceptions), (
            "All failures must be clean InsufficientStockError domain exceptions"
        )
        # Store inventory invariant: final_stock >= 0
        assert res.final_stock >= 0

    @pytest.mark.parametrize("trial_index", range(15))
    def test_multi_iteration_race_safety(self, trial_index: int) -> None:
        """Run multiple trials to prove consistent zero-overselling under load."""
        store = Store()
        p = Product(f"PROD-{trial_index}", "Hot Item", price_cents=2000, stock=1)
        store.add_product(p)

        res = run_concurrent_checkout_trial(
            store=store,
            product_id=p.id,
            num_threads=6,
            use_lock=True,
        )

        assert res.successful_checkouts == 1
        assert res.failed_checkouts == 5
        assert res.final_stock == 0
        assert res.final_stock >= 0

    def test_limited_batch_concurrency(self) -> None:
        """5 items in stock, 15 threads racing to buy 1 item each."""
        store = Store()
        p = Product("BATCH-01", "Limited Batch", price_cents=1000, stock=5)
        store.add_product(p)

        res = run_concurrent_checkout_trial(
            store=store,
            product_id=p.id,
            num_threads=15,
            use_lock=True,
        )

        assert res.successful_checkouts == 5
        assert res.failed_checkouts == 10
        assert res.final_stock == 0

    def test_demonstration_of_race_condition_without_lock(self) -> None:
        """Demonstrates race condition on inventory without locks.

        Demonstrates that omitting synchronization allows overselling (race condition).
        """
        store = Store()
        p = Product("UNSAFE-01", "Unprotected Item", price_cents=1000, stock=1)
        store.add_product(p)

        res = run_concurrent_checkout_trial(
            store=store,
            product_id=p.id,
            num_threads=6,
            use_lock=False,            # Intentionally omitting threading.Lock
            simulate_race_delay=0.003, # Widen read-modify-write gap to trigger race
        )

        # Without locks, multiple checkouts succeed despite only 1 item in stock (race condition)
        assert res.successful_checkouts > 1, (
            "Without locks, multiple threads should interleave in the read-modify-write gap"
        )
        # Store invariant violated: overselling occurred
        assert res.successful_checkouts > 1
        assert res.failed_checkouts < 5  # Instead of 5 rejections, threads improperly succeeded
