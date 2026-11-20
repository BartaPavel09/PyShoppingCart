"""Unit tests for custom iterators, generators, and pure functional reports."""

from __future__ import annotations

import pytest

from pyshoppingcart.models import Order, OrderItem, OrderStatus, Product
from pyshoppingcart.reporting import OrderBatchIterator, generate_order_summary, low_stock_scanner


class TestGeneratorsAndIterators:
    def test_low_stock_scanner(self) -> None:
        products = [
            Product("P1", "Abundant", 1000, 50),
            Product("P2", "Critical", 2000, 2),
            Product("P3", "Out", 1500, 0),
            Product("P4", "Normal", 3000, 10),
            Product("P5", "Low", 500, 5),
        ]
        low_stock = list(low_stock_scanner(products, threshold=5))
        assert len(low_stock) == 3
        ids = [p.id for p in low_stock]
        assert ids == ["P2", "P3", "P5"]

    def test_order_batch_iterator(self) -> None:
        orders = [
            Order(f"ORD-{i}", "C1", [OrderItem("P1", "X", 100, 1, 100)], 100, 0, 100)
            for i in range(1, 8)
        ]
        # 7 orders in batches of 3 -> batches of 3, 3, 1
        iterator = OrderBatchIterator(orders, batch_size=3)
        batches = list(iterator)
        assert len(batches) == 3
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 1

        with pytest.raises(ValueError):
            OrderBatchIterator(orders, batch_size=0)


class TestPureFunctionalReporting:
    def test_empty_order_summary(self) -> None:
        summary = generate_order_summary([])
        assert summary.total_orders == 0
        assert summary.total_revenue_cents == 0
        assert summary.average_order_value_cents == 0

    def test_order_summary_filtering_and_reduction(self) -> None:
        orders = [
            Order("O1", "ALICE", [OrderItem("P1", "Item", 1000, 2, 2000)], 2000, 200, 1800, status=OrderStatus.CONFIRMED),
            Order("O2", "BOB", [OrderItem("P2", "Item", 3000, 1, 3000)], 3000, 500, 2500, status=OrderStatus.CONFIRMED),
            Order("O3", "ALICE", [OrderItem("P1", "Item", 1000, 1, 1000)], 1000, 0, 1000, status=OrderStatus.CONFIRMED),
            Order("O4", "ALICE", [OrderItem("P3", "Item", 5000, 1, 5000)], 5000, 0, 5000, status=OrderStatus.CANCELLED),
        ]

        # Overall summary for confirmed orders only
        confirmed_summary = generate_order_summary(orders, status=OrderStatus.CONFIRMED)
        assert confirmed_summary.total_orders == 3
        # O1 (1800) + O2 (2500) + O3 (1000) = 5300
        assert confirmed_summary.total_revenue_cents == 5300
        assert confirmed_summary.total_discount_cents == 700
        # Units: O1 (2) + O2 (1) + O3 (1) = 4 units
        assert confirmed_summary.total_units_sold == 4
        assert confirmed_summary.average_order_value_cents == 5300 // 3

        # Filter by customer ALICE
        alice_summary = generate_order_summary(orders, customer_id="ALICE", status=OrderStatus.CONFIRMED)
        assert alice_summary.total_orders == 2
        assert alice_summary.total_revenue_cents == 1800 + 1000  # 2800 cents
        assert alice_summary.matching_order_ids == ("O1", "O3")

    def test_pure_function_immutability(self) -> None:
        # Verify that generating report does not mutate input sequence or orders
        order = Order("O1", "C1", [OrderItem("P1", "X", 1000, 1, 1000)], 1000, 100, 900)
        orders = [order]
        orders_tuple = tuple(orders)

        summary = generate_order_summary(orders)
        assert orders == list(orders_tuple)
        assert order.total_cents == 900
