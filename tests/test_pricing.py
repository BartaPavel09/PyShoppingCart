"""Unit tests for PyShoppingCart pricing and discount policies."""

from __future__ import annotations

import pytest

from pyshoppingcart.exceptions import DiscountError
from pyshoppingcart.models import Cart, Product
from pyshoppingcart.pricing import BulkThresholdDiscount, PercentageDiscount, PricingEngine


class TestDiscountPolicies:
    def test_percentage_discount_calculation(self) -> None:
        cart = Cart("C1")
        p = Product("P1", "Item", 10000, 5)  # $100.00
        cart.add_item(p, 1)

        promo = PercentageDiscount("SUMMER10", percentage=10)
        assert promo.is_applicable(cart, 10000)
        discount = promo.calculate_discount(cart, 10000)
        assert discount == 1000  # $10.00 in integer cents

    def test_percentage_discount_validation(self) -> None:
        with pytest.raises(DiscountError):
            PercentageDiscount("BAD", percentage=0)
        with pytest.raises(DiscountError):
            PercentageDiscount("BAD", percentage=101)

    def test_bulk_threshold_discount(self) -> None:
        cart = Cart("C1")
        p = Product("P1", "Item", 6000, 5)  # $60.00
        cart.add_item(p, 1)

        threshold = BulkThresholdDiscount(threshold_cents=10000, discount_cents=1500)
        # Not applicable below $100.00
        assert not threshold.is_applicable(cart, 6000)
        assert threshold.calculate_discount(cart, 6000) == 0

        # Add second item -> subtotal $120.00
        cart.add_item(p, 1)
        assert threshold.is_applicable(cart, 12000)
        assert threshold.calculate_discount(cart, 12000) == 1500  # $15.00 off


class TestPricingEngine:
    def test_empty_cart_pricing(self) -> None:
        engine = PricingEngine()
        cart = Cart("C1")
        res = engine.calculate_pricing(cart)
        assert res.subtotal_cents == 0
        assert res.discount_cents == 0
        assert res.total_cents == 0

    def test_sequential_discount_stacking(self) -> None:
        # Rules: BulkThreshold applied first against gross, then Percentage on remainder
        threshold = BulkThresholdDiscount(threshold_cents=10000, discount_cents=1500)  # -$15.00
        promo = PercentageDiscount("PROMO10", percentage=10)                            # 10%

        engine = PricingEngine(policies=[threshold, promo])
        cart = Cart("C1")
        cart.add_item(Product("P1", "Laptop", 20000, 5), 1)  # $200.00 = 20,000 cents

        res = engine.calculate_pricing(cart)
        assert res.subtotal_cents == 20000
        # Step 1: BulkThreshold reduces by 1500 -> balance 18500
        # Step 2: Percentage reduces 18500 by 10% -> 1850
        # Total discount: 1500 + 1850 = 3350 cents
        assert res.discount_cents == 3350
        assert res.total_cents == 20000 - 3350  # 16650 cents ($166.50)

    def test_zero_floor_guarantee(self) -> None:
        # When discounts reduce balance to 0, total must be clamped at exactly 0 cents (never negative)
        discount1 = BulkThresholdDiscount(threshold_cents=5000, discount_cents=5000)
        discount2 = BulkThresholdDiscount(threshold_cents=1000, discount_cents=1000)
        promo = PercentageDiscount("EXTRA50", percentage=50)

        engine = PricingEngine(policies=[discount1, discount2, promo])

        cart = Cart("C1")
        cart.add_item(Product("P1", "Item", 5000, 5), 1)  # subtotal $50.00 = 5000 cents

        res = engine.calculate_pricing(cart)
        assert res.subtotal_cents == 5000
        assert res.discount_cents == 5000
        assert res.total_cents == 0  # Guaranteed non-negative (>= 0)
