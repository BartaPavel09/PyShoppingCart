"""Bulk threshold discount policy for PyShoppingCart."""

from __future__ import annotations

from pyshoppingcart.exceptions import DiscountError
from pyshoppingcart.models.cart import Cart
from pyshoppingcart.pricing.base import DiscountPolicy


class BulkThresholdDiscount(DiscountPolicy):
    """Applies a fixed discount in cents if the cart subtotal meets or exceeds a threshold."""

    def __init__(
        self,
        threshold_cents: int,
        discount_cents: int,
        name_label: str = "Bulk Order Threshold Discount",
    ) -> None:
        if threshold_cents <= 0:
            raise DiscountError(f"Threshold must be > 0 cents, got {threshold_cents}.")
        if discount_cents <= 0:
            raise DiscountError(f"Discount must be > 0 cents, got {discount_cents}.")
        if discount_cents > threshold_cents:
            raise DiscountError(f"Discount ({discount_cents}) cannot exceed threshold ({threshold_cents}).")

        self.threshold_cents: int = threshold_cents
        self.discount_cents: int = discount_cents
        self.name_label: str = name_label

    @property
    def name(self) -> str:
        threshold_usd = self.threshold_cents / 100
        discount_usd = self.discount_cents / 100
        return f"{self.name_label} (${discount_usd:.2f} off orders over ${threshold_usd:.2f})"

    def is_applicable(self, cart: Cart, current_balance_cents: int) -> bool:
        return cart.subtotal_cents >= self.threshold_cents and current_balance_cents > 0

    def calculate_discount(self, cart: Cart, current_balance_cents: int) -> int:
        if not self.is_applicable(cart, current_balance_cents):
            return 0
        return min(self.discount_cents, current_balance_cents)

    def __repr__(self) -> str:
        return (
            f"BulkThresholdDiscount(threshold_cents={self.threshold_cents}, "
            f"discount_cents={self.discount_cents})"
        )
