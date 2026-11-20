"""Pure functional order analytics and reporting for PyShoppingCart."""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Callable, Iterable, Sequence

from pyshoppingcart.models.order import Order, OrderStatus
from pyshoppingcart.utils.formatters import cents_to_usd


@dataclass(frozen=True)
class OrderHistorySummary:
    """Immutable report summary computed by a pure functional pipeline."""
    total_orders: int
    total_revenue_cents: int
    total_discount_cents: int
    total_units_sold: int
    average_order_value_cents: int
    matching_order_ids: tuple[str, ...]

    def __str__(self) -> str:
        rev = cents_to_usd(self.total_revenue_cents)
        disc = cents_to_usd(self.total_discount_cents)
        aov = cents_to_usd(self.average_order_value_cents)
        return (
            f"=== Order History Report ===\n"
            f"Total Orders:     {self.total_orders}\n"
            f"Total Revenue:    {rev}\n"
            f"Total Discounts:  {disc}\n"
            f"Units Sold:       {self.total_units_sold}\n"
            f"Avg Order Value:  {aov}\n"
            f"Matching Orders:  {', '.join(self.matching_order_ids) if self.matching_order_ids else 'None'}"
        )


def generate_order_summary(
    orders: Sequence[Order],
    customer_id: str | None = None,
    status: OrderStatus | str | None = None,
    min_total_cents: int = 0,
) -> OrderHistorySummary:
    """Generate an analytical summary of orders using a pure functional pipeline.

    Architectural Rationale (Functional vs. Imperative):
    ---------------------------------------------------
      1. Declarative Intent over Step-by-Step Mutation:
         An imperative implementation relies on initializing mutable accumulators
         (e.g. `revenue = 0; count = 0; for o in orders: revenue += o.total_cents`).
         The functional approach uses `filter` and `map` to state *what* output
         is desired without procedural loop mechanics.
      2. Purity & Absence of Side Effects:
         This function does not mutate the input collection, objects, or any global
         state. Given the same inputs, it deterministically returns the exact same summary.
      3. Thread Safety & Immutability:
         Because no intermediate shared accumulator is mutated during computation,
         multiple concurrent worker threads can run reports on store history
         simultaneously without data races or lock contention.
      4. Composability:
         Filtering predicates and mapping transforms are modular callables that
         can be independently tested, reused, or swapped.

    Args:
        orders: Immutable sequence of orders to analyze.
        customer_id: Optional filter for a specific customer.
        status: Optional filter for order status (defaults to all if None).
        min_total_cents: Minimum total in cents threshold.

    Returns:
        Immutable OrderHistorySummary dataclass.
    """
    target_status = OrderStatus(status) if isinstance(status, (str, OrderStatus)) and status else None

    # Step 1: Compose declarative predicate using pure functions
    def matches_criteria(order: Order) -> bool:
        if customer_id and order.customer_id != customer_id:
            return False
        if target_status and order.status != target_status:
            return False
        if order.total_cents < min_total_cents:
            return False
        return True

    # Step 2: Declarative filtering using filter()
    filtered_orders: list[Order] = list(filter(matches_criteria, orders))

    total_count = len(filtered_orders)
    if total_count == 0:
        return OrderHistorySummary(
            total_orders=0,
            total_revenue_cents=0,
            total_discount_cents=0,
            total_units_sold=0,
            average_order_value_cents=0,
            matching_order_ids=(),
        )

    # Step 3: Declarative mapping using map() and reduction
    revenues = list(map(lambda o: o.total_cents, filtered_orders))
    discounts = list(map(lambda o: o.discount_cents, filtered_orders))
    units_per_order = list(map(lambda o: sum(item.quantity for item in o.items), filtered_orders))

    # Aggregations using sum and functools.reduce
    total_revenue = reduce(lambda acc, val: acc + val, revenues, 0)
    total_discount = sum(discounts)
    total_units = sum(units_per_order)
    average_order_value = total_revenue // total_count

    matching_ids = tuple(map(lambda o: o.id, filtered_orders))

    return OrderHistorySummary(
        total_orders=total_count,
        total_revenue_cents=total_revenue,
        total_discount_cents=total_discount,
        total_units_sold=total_units,
        average_order_value_cents=average_order_value,
        matching_order_ids=matching_ids,
    )
