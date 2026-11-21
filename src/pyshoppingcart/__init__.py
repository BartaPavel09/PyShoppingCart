"""PyShoppingCart - Core E-Commerce Store Backend and Utilities.

Designed for Python 3.11+ with strict typing and thread-safe inventory operations.
"""

from pyshoppingcart.models import Cart, CartItem, Customer, Order, OrderItem, OrderStatus, Product
from pyshoppingcart.pricing import (
    BulkThresholdDiscount,
    DiscountPolicy,
    PercentageDiscount,
    PricingEngine,
    PricingResult,
)
from pyshoppingcart.reporting import OrderBatchIterator, OrderHistorySummary, generate_order_summary, low_stock_scanner
from pyshoppingcart.store import Store
from pyshoppingcart.utils import cents_to_usd, log_state_transition, timed_operation, usd_to_cents

__all__ = [
    "Product",
    "Customer",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatus",
    "DiscountPolicy",
    "PercentageDiscount",
    "BulkThresholdDiscount",
    "PricingEngine",
    "PricingResult",
    "Store",
    "low_stock_scanner",
    "OrderBatchIterator",
    "OrderHistorySummary",
    "generate_order_summary",
    "timed_operation",
    "log_state_transition",
    "cents_to_usd",
    "usd_to_cents",
]
